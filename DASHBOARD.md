# Minecraft AI Agent - Comprehensive Dashboard

A full-featured Steam-style admin dashboard for managing and monitoring your Minecraft AI Agent in real-time.

## 📋 Overview

The dashboard provides a unified interface for:
- **Live Monitoring**: Real-time log streaming and game state tracking
- **Player Management**: Inventory, kills, deaths, and equipment tracking
- **Challenge System**: Create, track, and reward player challenges
- **Recipe Library**: Browse 115+ crafting recipes
- **AI Interaction**: Chat with the AI agent with command support
- **Analytics**: Session analysis and tactical reports

## 📄 Pages

### 1. **Dashboard**
Home page with quick overview:
- Session statistics (total events, kills, deaths, health warnings)
- Active challenge status
- Recent events timeline
- AI agent status

**Key Features:**
- Real-time stat updates
- Event feed
- Quick access buttons
- Sidebar widget for active challenge

### 2. **Live Logs**
Real-time log streaming with filtering:
- WebSocket-powered live updates
- Level filtering (INFO, WARNING, ERROR)
- Auto-scroll toggle
- Clear logs button
- Color-coded log levels

**Log Types:**
- `INFO`: General game events
- `WARNING`: Health warnings, item stack issues
- `ERROR`: Critical failures

### 3. **Challenges**
Challenge management system:
- **Create** new challenges (kill/collect goals)
- **View** active challenge with progress bar
- **Track** challenge history (completed/cancelled)
- **Claim** rewards upon completion
- **Cancel** active challenges

**Challenge Fields:**
- Title & Description
- Goal Type: Kill or Collect
- Target Entity/Item ID
- Count goal
- Reward Item & Count

### 4. **Inventory**
Player equipment and items:
- **Inventory**: All collected items with counts
- **Equipment**: Armor pieces (helmet, chestplate, etc.)
- **Hotbar**: Quick access items (slots 1-9)
- **Offhand**: Secondary hand slot

Each section displays localized item names with quantities.

### 5. **Crafting**
Recipe browser with search:
- 115+ Minecraft recipes
- Search by name or ID
- Category filtering (tools, weapons, armor, blocks, decoration)
- Recipe details with emoji indicators
- 3x3 crafting grid visualization (via steam.html)

**Categories:**
- 🔨 Tools: Pickaxes, axes, shovels, hoes
- ⚔️ Weapons: Swords, bows, arrows
- 🛡️ Armor: All armor sets (leather, iron, diamond, gold)
- 🧱 Blocks: Building materials and decorative blocks
- 🎨 Decoration: Furniture, lights, plants
- ⚡ Redstone: Mechanisms and automation

### 6. **Chat AI**
Interactive AI agent communication:
- Real-time messaging interface
- Built-in command examples
- Tool-based actions (give items, summon entities, create challenges)
- Message history in sidebar

**Available Commands:**
```
give me [item]              → Request an item
summon [mob]               → Summon an entity
create challenge [desc]    → Create a new challenge
claim reward               → Claim challenge reward
```

### 7. **Analytics**
Session analysis and reporting:
- Post-match tactical analysis
- Death count and circumstances
- Health crisis timeline
- LLM-powered insights
- Session statistics summary

**Report Includes:**
- Total events count
- Death analysis
- Low health warnings
- Hostile encounter statistics
- Event timeline

## 🎨 Design System

### Color Palette
- **Primary**: `#1b2838` (Dark Navy)
- **Secondary**: `#0c1419` (Darker Navy)
- **Accent**: `#1e90ff` (Bright Blue)
- **Text Primary**: `#c7d5e0` (Light Gray)
- **Text Secondary**: `#8892a1` (Medium Gray)
- **Success**: `#76c043` (Green)
- **Warning**: `#f5a623` (Orange)
- **Danger**: `#c41e3a` (Red)

### Layout
- **Header**: Sticky navigation with connection status
- **Sidebar**: Fixed left panel with stats and quick actions
- **Main Content**: Responsive grid layout for pages
- **Modals**: Centered dialogs for forms and confirmations

## 🔌 API Integration

All pages connect to real API endpoints:

| Endpoint | Purpose | Method |
|----------|---------|--------|
| `/api/logs/` | Get game logs | GET |
| `/api/logs/ws` | Real-time log stream | WebSocket |
| `/api/player-state/` | Player statistics | GET |
| `/api/player-state/inventory` | Inventory data | GET |
| `/api/player-state/kills` | Kill statistics | GET |
| `/api/challenges/` | Challenge management | GET/POST |
| `/api/challenges/{id}/claim` | Claim reward | POST |
| `/api/challenges/{id}/cancel` | Cancel challenge | POST |
| `/api/rp/chat` | AI chat | POST |
| `/api/analytics/session_summary` | Session analysis | GET |
| `/api/recipes` | Recipe database | GET |

## 🚀 Usage

### Accessing the Dashboard
```
http://localhost:8000/
http://localhost:8000/dashboard
```

### Creating a Challenge
1. Navigate to **Challenges** page
2. Click **+ New Challenge** button
3. Fill in challenge details:
   - Title: "Creeper Slayer"
   - Description: "Kill 5 creepers"
   - Goal Type: Kill
   - Target: creeper
   - Count: 5
   - Reward: emerald (1x)
4. Click **Create**

### Monitoring Live Logs
1. Go to **Live Logs** page
2. Select log level filter (optional)
3. Logs update in real-time via WebSocket
4. Toggle **Auto Scroll** to pause at specific events
5. Click **Clear** to reset log view

### Searching Recipes
1. Navigate to **Crafting** page
2. Type in search box (e.g., "iron pickaxe")
3. Use category dropdown to filter
4. Click recipe to view details
5. Switch to **steam.html** for full recipe view with grid

### Checking Inventory
1. Go to **Inventory** page
2. View items grouped by location:
   - Main inventory grid
   - Equipped armor
   - Hotbar slots
   - Offhand item
3. Displays localized item names and counts

### Using AI Chat
1. Navigate to **Chat AI** page
2. Type command or message in input box
3. Press Enter or click **Send**
4. AI responds with actions or messages
5. Available commands listed below chat area

### Generating Session Analysis
1. Go to **Analytics** page
2. Click **Generate Report**
3. Report generates post-match analysis including:
   - Deaths and circumstances
   - Health crises
   - Combat encounters
   - LLM-powered insights

## 🔧 Technical Details

### WebSocket Connection
- Auto-reconnecting to log stream
- 3-second retry on disconnect
- Connection status indicator in header

### Real-time Updates
- Logs update instantly via WebSocket
- Sidebar stats refresh on log events
- Challenge progress updates automatically
- Player state syncs with game events

### Responsive Breakpoints
- **Mobile**: < 768px (single column, minimal sidebar)
- **Tablet**: 768px - 1024px (2-column layout)
- **Desktop**: > 1024px (full layout with sidebar)

### Performance
- Logs capped at 100 entries on load
- WebSocket reconnection with exponential backoff
- Lazy loading of page-specific data
- Efficient DOM updates

## 📦 File Structure

```
static/
├── dashboard.html       # Main dashboard interface
├── dashboard.css        # Styling (17.7 KB)
├── dashboard.js         # Interactive features
├── steam.html          # Crafting recipe viewer
├── steam.css           # Recipe styling
└── steam.js            # Recipe features
```

## 🎯 Features Summary

| Feature | Status | Details |
|---------|--------|---------|
| Real-time logs | ✅ | WebSocket streaming |
| Player state | ✅ | Kills, deaths, inventory |
| Challenge system | ✅ | Create, track, claim |
| Recipe browser | ✅ | 115+ recipes, search |
| AI chat | ✅ | Command support |
| Analytics | ✅ | LLM-powered analysis |
| Responsive design | ✅ | Mobile to desktop |
| Dark theme | ✅ | Steam color palette |

## 🔮 Future Enhancements

- [ ] Player profile page with statistics
- [ ] Leaderboard system
- [ ] Achievement tracking
- [ ] Multi-player support
- [ ] Custom themes
- [ ] Data export (CSV, JSON)
- [ ] Replay functionality
- [ ] Voice command support
- [ ] Mobile app native version
- [ ] Cloud synchronization

## 🐛 Troubleshooting

### WebSocket Connection Fails
- Check server is running on `http://localhost:8000`
- Check browser console for errors
- Verify firewall allows WebSocket connections

### Logs Not Updating
- Ensure game is running and logging events
- Check /api/logs/ endpoint responds
- Try refreshing page

### Challenge Creation Error
- Ensure target ID is valid (entity/item)
- Reward item must be valid Minecraft item
- Check console for validation errors

### Inventory Empty
- Verify player state has been populated
- Check game is sending inventory updates
- Try running game and checking logs first

## 📞 Support

For issues or feature requests, check:
- Browser console for error messages
- WebSocket connection status
- API endpoint availability
- Game client logs

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Status**: Production Ready
