# Glass Cutting Optimizer Pro

A professional desktop application for optimizing glass sheet cutting layouts, designed specifically for glass businesses in South Africa. Minimize waste, maximize efficiency, and generate professional cutting plans with PDF export.

![Glass Cutting Optimizer Pro](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

## 🎯 Features

### Core Functionality
- **Multi-Sheet Support** - Add multiple sheet sizes with quantities, optimizer automatically selects the best sheet for each piece
- **Intelligent Optimization** - Uses advanced algorithms to minimize waste and maximize material efficiency
- **Customer Labels** - Each piece displays customer name, dimensions, and piece numbers (e.g., "1/3, 2/3, 3/3")
- **Automatic Rotation** - Pieces are automatically rotated 90° when it improves fit
- **PDF Export** - Generate professional cutting plans with visual diagrams and detailed cutting lists

### Professional Controls
- **Multiple Units** - Work in millimeters, centimeters, inches, or meters
- **Blade Width Compensation** - Account for saw kerf/blade width in calculations
- **Max Cut Length Limit** - Set maximum cut length for manual cutting constraints
- **Min Useful Waste** - Define minimum size for offcuts worth keeping (smaller = garbage)
- **Min Part Size** - Prevent breakable parts by setting minimum dimensions
- **Automatic Offcuts Handling** - Useful waste is automatically saved to inventory and reused

### Waste Management
- **Offcuts Inventory** - Automatically tracks reusable waste pieces
- **Smart Material Usage** - Optimizer tries offcuts first before using new sheets
- **Efficiency Metrics** - Real-time display of waste percentage and material usage
- **Waste Visualization** - See exactly where material is being wasted

## 📸 Screenshots

### Main Interface
Intuitive layout with sheet inventory, customer orders, and optimization settings.

### Optimized Layout
Visual cutting diagrams showing exactly where each piece should be cut, with customer labels and rotation indicators.

### PDF Export
Professional cutting plans ready to print and take to the workshop.

## 🚀 Installation

### For End Users

1. Download the latest `Glass-Cutting-Optimizer-Setup.exe` from the [Releases](../../releases) page
2. Run the installer
3. Launch "Glass Cutting Optimizer Pro" from your desktop or start menu

**Note**: Windows may show a security warning since the app isn't code-signed. Click "More info" → "Run anyway" to proceed.

### For Developers

#### Prerequisites
- [Node.js](https://nodejs.org) (v16 or higher)
- npm (comes with Node.js)

#### Build from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/glass-cutting-optimizer.git
   cd glass-cutting-optimizer
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run in development mode:
   ```bash
   npm start
   ```

4. Build installer:
   ```bash
   npm run build-win    # Windows
   npm run build-mac    # macOS
   npm run build        # Current platform
   ```

The installer will be created in the `dist` folder.

## 📖 Usage Guide

### Getting Started

1. **Configure Sheet Sizes**
   - Click "Available Sheets" section
   - Add your standard glass sheet sizes (e.g., 3000×2000mm)
   - Set quantity for each size (999 = unlimited)
   - Label each type for easy identification

2. **Adjust Settings** (Optional)
   - Click the settings gear icon
   - Set your blade width (kerf)
   - Configure max cut length for manual cutting
   - Set minimum useful waste size
   - Set minimum part size to prevent breakage

3. **Add Customer Orders**
   - Enter customer name
   - Input dimensions (width × height)
   - Set quantity of pieces needed
   - Click "Add Order"

4. **Optimize Layout**
   - Review all orders in the list
   - Click "Optimize Layout"
   - The app automatically selects best sheets and arranges pieces

5. **Export to PDF**
   - Click "Export to PDF" button
   - Save the cutting plan
   - Print or share with your workshop

### Understanding the Results

- **Sheet Diagrams**: Visual layout showing where each piece should be cut
- **Customer Labels**: Each piece shows customer name, dimensions, and piece number
- **Rotation Indicator**: "↻ ROTATED" shows pieces turned 90° for better fit
- **Cutting List**: Detailed list below each diagram for reference
- **Efficiency**: Percentage of material used vs wasted
- **Sheet Type**: Shows which sheet size was used (Standard, Large, etc.)

## 🔧 Configuration

### Default Settings

```javascript
// Sheet Settings
Default Sheet: 3000×2000mm (unlimited quantity)
Unit: Millimeters (mm)

// Cutting Parameters
Blade Width: 3mm
Max Cut Length: 3000mm
Min Useful Waste: 300mm
Min Part Size: 100mm
```

### Customization

#### Change Default Sheet Size
Edit `index.html` and modify:
```javascript
const [availableSheets, setAvailableSheets] = useState([
    { id: 1, width: 3000, height: 2000, quantity: 999, label: 'Standard Sheet' }
]);
```

#### Change Default Unit
```javascript
const [unit, setUnit] = useState('mm'); // Change to 'cm', 'in', or 'm'
```

#### Adjust Default Parameters
```javascript
const [bladeWidth, setBladeWidth] = useState(3);
const [maxCutLength, setMaxCutLength] = useState(3000);
const [minUsefulWaste, setMinUsefulWaste] = useState(300);
const [minPartSize, setMinPartSize] = useState(100);
```

## 🏗️ Project Structure

```
glass-cutting-optimizer/
├── icon.ico              # Application icon (Windows)
├── icon.png              # Application icon (general)
├── package.json          # Project configuration & dependencies
├── main.js               # Electron main process
├── index.html            # Application UI and logic
├── node_modules/         # Dependencies (generated)
├── dist/                 # Build output (generated)
└── README.md             # This file
```

## 🛠️ Technologies Used

- **Electron** - Cross-platform desktop application framework
- **React** - UI library for interactive components
- **Tailwind CSS** - Utility-first CSS framework
- **jsPDF** - PDF generation library
- **electron-builder** - Application packaging and distribution

## 🧮 Optimization Algorithm

The optimizer uses a **Best-Fit Decreasing (BFD)** algorithm with the following strategy:

1. **Sort pieces** by area (largest first)
2. **Try offcuts** - Check existing waste pieces first
3. **Fill existing sheets** - Add to partially-filled sheets when efficient
4. **Select best new sheet** - Choose sheet size that minimizes waste
5. **Handle rotation** - Automatically rotate pieces for better fit
6. **Respect constraints** - Honor max cut length and min part size limits
7. **Track waste** - Save useful offcuts to inventory for future use

### Optimization Priorities
1. Reuse offcuts (minimize new material)
2. Fill partially-used sheets (consolidate waste)
3. Choose appropriately-sized sheets (prevent oversizing)
4. Maximize efficiency while respecting constraints

## 📊 Performance

- Handles 100+ pieces efficiently
- Real-time optimization (< 2 seconds for typical jobs)
- Supports unlimited sheet types
- Manages offcuts inventory automatically

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 Roadmap

### Planned Features
- [ ] Save/Load project files
- [ ] Import orders from CSV
- [ ] Advanced nesting algorithms
- [ ] Material cost calculations
- [ ] Multi-language support
- [ ] Cloud sync for offcuts inventory
- [ ] Print directly from app

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

Built with ❤️ for the glass cutting industry in South Africa

## 🙏 Acknowledgments

- Thanks to the South African glass industry for feedback and requirements
- Inspired by the need for efficient material usage and waste reduction
- Built with modern web technologies for cross-platform compatibility

## 📞 Support

For issues, questions, or feature requests, please [open an issue](../../issues) on GitHub.

## 🌟 Star History

If this project helps your business, please consider giving it a star! ⭐

---

**Made for glass cutters, by developers who care about efficiency** 🪟✂️

## 💡 Tips for Best Results

1. **Measure accurately** - Double-check all dimensions before adding orders
2. **Update offcuts regularly** - Remove used offcuts from inventory
3. **Adjust blade width** - Set to your actual saw kerf for accurate results
4. **Use appropriate units** - Stick to one unit system throughout
5. **Export PDFs** - Keep digital records of all cutting plans
6. **Label sheets clearly** - Use descriptive names for different sheet types
7. **Review efficiency** - If efficiency is low, consider reordering piece sizes

## 🔐 Privacy & Data

- **All data is local** - Nothing is sent to external servers
- **No internet required** - Works completely offline
- **No tracking** - No analytics or telemetry
- **Your data stays yours** - Export PDFs or keep in the app
