# Glass Cutting Optimizer Pro

A professional desktop application for optimizing glass sheet cutting layouts, designed specifically for glass businesses in South Africa. Minimize waste, maximize material efficiency, and generate professional cutting plans with direct PDF export.

![Glass Cutting Optimizer Pro](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

## 🎯 Features

**Core Functionality**
* **Multi-Sheet Support**: Add multiple sheet sizes with custom quantities; the optimizer automatically selects the ideal sheet per piece.
* **Intelligent Optimization**: Employs advanced algorithms to minimize waste and maximize material efficiency.
* **Customer Labels**: Displays customer details, cut dimensions, and piece numbering (e.g., "1/3, 2/3, 3/3").
* **Automatic Rotation**: Automatically rotates pieces 90° when it improves fit.
* **PDF Export**: Generates professional cutting plans complete with visual diagrams and detailed cutting lists.

**Professional Controls**
* **Multiple Units**: Toggle between millimeters (mm), centimeters (cm), inches (in), or meters (m).
* **Blade Width Compensation**: Accounts for saw kerf and blade width directly in calculations.
* **Max Cut Length Limit**: Sets upper cut boundaries to support manual cutting constraints.
* **Min Useful Waste**: Sets threshold limits for reusable offcuts (smaller offcuts are flagged as scrap).
* **Min Part Size**: Helps prevent material breakage by establishing minimum allowable part dimensions.
* **Automatic Offcuts Handling**: Useful waste is automatically tracked and prioritized for future cutting jobs.

**Waste Management**
* **Offcuts Inventory**: Automatically tracks reusable offcut inventory.
* **Smart Material Usage**: Prioritizes existing offcut stock before cutting new sheets.
* **Efficiency Metrics**: Real-time visualization of material yield and waste percentages.

## 🚀 Quick Start & Installation

> **Note**: Windows SmartScreen may display a warning if the executable is un-signed. Click **More Info** → **Run Anyway** to launch.

**Build Setup**

1. Clone the repository:
   ```bash
   git clone https://github.com/conner-dav/glass-optimizing-software/
   cd glass-optimizing-software
