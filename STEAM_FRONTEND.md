# Steam-Style Minecraft Crafting Frontend

A modern, dark-themed web interface for browsing and managing Minecraft crafting recipes, inspired by Valve's Steam platform design.

## Features

### Core UI Elements
- **Dark Theme**: Steam color palette with dark grays, accent blues, and smooth gradients
- **Sticky Header**: Navigation bar with logo, main menu, and user profile
- **Persistent Sidebar**: Quick access navigation with category filters
- **Responsive Layout**: Adapts to mobile, tablet, and desktop screens

### Recipe Management
- **115+ Recipes**: Complete Minecraft crafting database
- **Smart Categorization**:
  - 🔨 Tools (pickaxes, axes, shovels, hoes)
  - ⚔️ Weapons (swords, bows, arrows)
  - 🛡️ Armor (leather, iron, diamond, gold sets)
  - 🧱 Blocks (building materials, decorative blocks)
  - 🎨 Decoration (furniture, lights, plants)
  - ⚡ Redstone (mechanisms, automation devices)

### Search & Discovery
- **Full-text Search**: Search recipes by name, ID, or description
- **Advanced Filters**: Category-based and favorite filtering
- **Sorting Options**: By name, popularity, or recent
- **Wiki Search**: Secondary search interface for discovery

### User Features
- **Favorite System**: Mark favorite recipes with star (⭐)
- **Local Storage**: Favorites persisted in browser
- **Recipe Modal**: Detailed view with 3x3 crafting grid
- **Statistics**: Track completion percentage and usage stats
- **User Preferences**: Settings for display and notifications

## File Structure

```
static/
├── steam.html          # Main interface structure
├── steam.css           # Styling (18KB, dark theme)
├── steam.js            # Interactive features
└── ...

data/
└── minecraft_crafting_recipes.json  # 115+ recipes
```

## API Endpoints

- `GET /` - Main Steam frontend (redirects to steam.html)
- `GET /steam` - Steam frontend
- `GET /api/recipes` - Get all recipes in JSON format

## Design System

### Colors
- Primary: `#1b2838` (dark navy)
- Secondary: `#0c1619` (darker navy)
- Accent: `#1e90ff` (bright blue)
- Text Primary: `#c7d5e0` (light gray)
- Text Secondary: `#8892a1` (medium gray)
- Border: `#2a3f5f` (dark blue-gray)

### Typography
- Font Family: System UI sans-serif
- Heading: 20-28px, bold
- Body: 14px, normal
- Label: 12px, uppercase

### Spacing
- XS: 4px
- SM: 8px
- MD: 16px
- LG: 24px
- XL: 32px

## Usage

### Access the Frontend
```
http://localhost:8000/
http://localhost:8000/steam
```

### Search Recipes
1. Click "Crafting Library" in navigation
2. Type in search bar to find recipes
3. Use category filters for browsing
4. Click cards to view detailed crafting grid

### Manage Favorites
1. Open recipe modal (click any recipe card)
2. Click "⭐ Add to Favorites" button
3. Favorites are saved automatically
4. View all favorites with the star filter

### Export/Import
- Settings panel includes data export options
- Favorites stored in browser's localStorage
- Can be backed up manually

## Performance

- **Initial Load**: ~200ms (recipes loaded from API)
- **Search**: Real-time (instant results)
- **Page Transitions**: 300ms fade animation
- **Caching**: Recipes cached in JavaScript memory

## Browser Support

- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Responsive Breakpoints

- Mobile: < 768px (single column, collapsible sidebar)
- Tablet: 768px - 1024px (2-column grid)
- Desktop: > 1024px (full layout)

## Recent Updates

### v1.0.0 (Current)
- Initial Steam-style design release
- 115+ crafting recipes
- Complete recipe database
- Favorite system with persistence
- Statistics dashboard
- Wiki search functionality
- Mobile-responsive layout

## Future Enhancements

- [ ] Recipe comparison tool
- [ ] Custom recipe creation
- [ ] Recipe history/recently viewed
- [ ] Multi-player favorites sync (cloud)
- [ ] Recipe difficulty ratings
- [ ] Video tutorials integration
- [ ] Achievement system
- [ ] Recipe collections/guides
