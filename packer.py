"""
Guillotine 2D cutting-stock optimizer for glass/wood cutting.

Core idea:
- You have a set of STOCK sheets (width x height, quantity available,
  optionally tagged with a material + texture, e.g. "6mm Float" / "Clear").
- You have a set of DEMAND pieces (width x height, quantity needed, optional
  "allow rotation" flag, optionally tagged with the same material + texture,
  plus which customer/job they belong to).
- Pieces are only ever cut from stock sheets with a matching material AND
  texture (a "Frosted" piece should never get cut from a "Clear" sheet) --
  each material/texture group is optimized independently, then merged.
  Leaving material/texture blank on everything (the default) disables this
  and behaves as one big pool, same as before.
- We place pieces onto sheets using guillotine cuts only (every cut goes
  edge-to-edge across the remaining rectangle), which is what a straight
  glass cutter / panel saw needs.
- Output: for each sheet used, the list of placed pieces with their
  x/y/width/height, plus leftover waste rectangles and utilization %.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import itertools


@dataclass
class Piece:
    label: str
    width: float
    height: float
    qty: int
    allow_rotation: bool = True
    material: str = ""
    texture: str = ""
    customer: str = ""


@dataclass
class StockSheet:
    label: str
    width: float
    height: float
    qty: int
    material: str = ""
    texture: str = ""
    price: float = 0.0  # cost per sheet, optional


@dataclass
class Placement:
    label: str
    x: float
    y: float
    width: float
    height: float
    rotated: bool
    customer: str = ""


@dataclass
class SheetResult:
    sheet_label: str
    sheet_width: float
    sheet_height: float
    price: float = 0.0
    placements: List[Placement] = field(default_factory=list)
    waste_rects: List[tuple] = field(default_factory=list)  # (x, y, w, h)
    cut_length: float = 0.0  # sum of guillotine cut lengths made on this sheet

    @property
    def used_area(self):
        return sum(p.width * p.height for p in self.placements)

    @property
    def utilization(self):
        total = self.sheet_width * self.sheet_height
        return 0.0 if total <= 0 else self.used_area / total


def group_sheet_results(sheet_results):
    """
    Collapse sheets that have an identical cutting layout (same stock size
    and same set of piece placements) into one representative + a repeat
    count, so the UI can show "Layout #1, quantity = 4" instead of printing
    the same picture four times.

    Returns a list of dicts: {"sheet": SheetResult, "count": int}
    """
    groups = []
    index_by_signature = {}
    for r in sheet_results:
        sig = (
            r.sheet_label, round(r.sheet_width, 3), round(r.sheet_height, 3),
            tuple(sorted(
                (p.label, round(p.x, 2), round(p.y, 2), round(p.width, 2), round(p.height, 2), p.rotated)
                for p in r.placements
            ))
        )
        if sig in index_by_signature:
            groups[index_by_signature[sig]]["count"] += 1
        else:
            index_by_signature[sig] = len(groups)
            groups.append({"sheet": r, "count": 1})
    return groups


@dataclass
class OverallStats:
    sheets_used: int
    total_sheet_area: float
    total_used_area: float
    total_waste_area: float
    overall_utilization: float
    total_cut_length: float
    total_cost: float
    pieces_placed: int
    pieces_unplaced: int


def compute_stats(sheet_results, unplaced) -> OverallStats:
    total_sheet_area = sum(r.sheet_width * r.sheet_height for r in sheet_results)
    total_used_area = sum(r.used_area for r in sheet_results)
    total_waste = total_sheet_area - total_used_area
    return OverallStats(
        sheets_used=len(sheet_results),
        total_sheet_area=total_sheet_area,
        total_used_area=total_used_area,
        total_waste_area=total_waste,
        overall_utilization=(total_used_area / total_sheet_area) if total_sheet_area else 0.0,
        total_cut_length=sum(r.cut_length for r in sheet_results),
        total_cost=sum(r.price for r in sheet_results),
        pieces_placed=sum(len(r.placements) for r in sheet_results),
        pieces_unplaced=len(unplaced),
    )


class FreeRect:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def area(self):
        return self.w * self.h


def _expand_pieces(pieces: List[Piece]):
    """Turn (piece, qty) into a flat list of individual piece instances,
    largest area first (classic first-fit-decreasing ordering)."""
    expanded = []
    for p in pieces:
        for _ in range(p.qty):
            expanded.append(p)
    expanded.sort(key=lambda p: p.width * p.height, reverse=True)
    return expanded


def _best_free_rect_for(piece: Piece, free_rects: List[FreeRect], kerf: float):
    """
    Find the best free rectangle to place this piece into.
    Tries both orientations if rotation is allowed.
    Returns (index_in_free_rects, chosen_w, chosen_h, rotated) or None.
    Uses "best area fit": smallest free rect that still fits the piece.
    """
    best = None  # (leftover_area, idx, w, h, rotated)
    orientations = [(piece.width, piece.height, False)]
    if piece.allow_rotation and piece.width != piece.height:
        orientations.append((piece.height, piece.width, True))

    for idx, rect in enumerate(free_rects):
        for w, h, rotated in orientations:
            needed_w = w + (kerf if w < rect.w else 0)  # kerf only matters if not last piece, simplified below
            if w <= rect.w + 1e-9 and h <= rect.h + 1e-9:
                leftover = rect.area - (w * h)
                if best is None or leftover < best[0]:
                    best = (leftover, idx, w, h, rotated)
    return best


def _split_free_rect(rect: FreeRect, used_w: float, used_h: float, kerf: float):
    """
    Split a free rectangle after placing a piece of size used_w x used_h
    in its top-left corner, using a guillotine cut. Returns (new_rects, cut_length):
      new_rects: up to two new FreeRects (right-of-piece, below-piece), choosing
                 the split axis that keeps the larger leftover piece as one
                 single rectangle (shorter-leftover-axis heuristic).
      cut_length: length of the single guillotine cut line made across this
                  rectangle to free up the piece's space (for reporting total
                  cutting length).
    """
    right_w = rect.w - used_w - kerf
    below_h = rect.h - used_h - kerf
    new_rects = []

    # Decide split orientation: compare leftover width vs leftover height
    if right_w <= below_h:
        # Horizontal cut first: full-width strip below, remaining rect to the right (piece height only)
        cut_length = rect.w
        if below_h > 1e-6:
            new_rects.append(FreeRect(rect.x, rect.y + used_h + kerf, rect.w, below_h))
        if right_w > 1e-6:
            new_rects.append(FreeRect(rect.x + used_w + kerf, rect.y, right_w, used_h))
    else:
        # Vertical cut first: full-height strip to the right, remaining rect below (piece width only)
        cut_length = rect.h
        if right_w > 1e-6:
            new_rects.append(FreeRect(rect.x + used_w + kerf, rect.y, right_w, rect.h))
        if below_h > 1e-6:
            new_rects.append(FreeRect(rect.x, rect.y + used_h + kerf, used_w, below_h))

    return new_rects, cut_length


def _optimize_pool(stock_sheets: List[StockSheet], pieces: List[Piece], kerf: float,
                    min_useful_waste: float):
    """
    Runs the guillotine packing optimization over ONE pool of mutually-
    compatible stock + pieces (i.e. already filtered to one material/texture
    group). See optimize() below for the public, material-aware entry point.
    """
    remaining = _expand_pieces(pieces)
    sheet_results: List[SheetResult] = []

    # Build a flat, repeated list of available physical sheets (respecting qty),
    # largest area first so bigger pieces get a chance on big sheets.
    available_sheets = []
    for s in stock_sheets:
        for _ in range(s.qty):
            available_sheets.append(s)
    available_sheets.sort(key=lambda s: s.width * s.height, reverse=True)

    sheet_idx = 0
    while remaining and sheet_idx < len(available_sheets):
        sheet = available_sheets[sheet_idx]
        sheet_idx += 1
        free_rects = [FreeRect(0, 0, sheet.width, sheet.height)]
        result = SheetResult(sheet.label, sheet.width, sheet.height, price=getattr(sheet, "price", 0.0))

        placed_this_sheet = True
        while placed_this_sheet and remaining:
            placed_this_sheet = False
            for i, piece in enumerate(remaining):
                best = _best_free_rect_for(piece, free_rects, kerf)
                if best is None:
                    continue
                leftover, ridx, w, h, rotated = best
                rect = free_rects.pop(ridx)
                result.placements.append(Placement(piece.label, rect.x, rect.y, w, h, rotated,
                                                     customer=getattr(piece, "customer", "")))
                split_rects, cut_len = _split_free_rect(rect, w, h, kerf)
                result.cut_length += cut_len
                free_rects.extend(split_rects)
                # drop any free rects too small to ever matter
                free_rects = [r for r in free_rects if r.w > 1e-6 and r.h > 1e-6]
                remaining.pop(i)
                placed_this_sheet = True
                break  # restart scan of remaining pieces against updated free_rects

        # Whatever free space is left over becomes recorded waste
        result.waste_rects = [(r.x, r.y, r.w, r.h) for r in free_rects
                               if r.w * r.h >= min_useful_waste]
        sheet_results.append(result)

    return sheet_results, remaining


def _norm(s):
    return (s or "").strip().lower()


def optimize(stock_sheets: List[StockSheet], pieces: List[Piece], kerf: float = 0.0,
             min_useful_waste: float = 0.0):
    """
    Run the guillotine packing optimization, keeping pieces on stock of the
    same material + texture only.

    Returns (sheet_results, unplaced_pieces)
      sheet_results: list of SheetResult, one per physical sheet actually used
      unplaced_pieces: list of dicts (label, width, height, reason) that
                       could not be placed. reason is either "no matching
                       stock (material/texture)" or "out of stock".
    """
    groups = {}  # (material, texture) -> {"stock": [...], "pieces": [...]}
    for s in stock_sheets:
        key = (_norm(s.material), _norm(s.texture))
        groups.setdefault(key, {"stock": [], "pieces": []})["stock"].append(s)
    for p in pieces:
        key = (_norm(p.material), _norm(p.texture))
        groups.setdefault(key, {"stock": [], "pieces": []})["pieces"].append(p)

    all_results: List[SheetResult] = []
    all_unplaced = []

    for key, group in groups.items():
        if not group["pieces"]:
            continue  # stock with no matching demand -- nothing to do
        if not group["stock"]:
            for p in group["pieces"]:
                for _ in range(p.qty):
                    all_unplaced.append({"label": p.label, "width": p.width, "height": p.height,
                                          "reason": "no matching stock (material/texture)"})
            continue

        results, remaining = _optimize_pool(group["stock"], group["pieces"], kerf, min_useful_waste)
        all_results.extend(results)
        for p in remaining:
            all_unplaced.append({"label": p.label, "width": p.width, "height": p.height,
                                  "reason": "out of stock"})

    return all_results, all_unplaced
