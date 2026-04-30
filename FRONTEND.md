# 🎮 Minecraft AI Agent - Complete Project

A sophisticated AI-powered Minecraft admin dashboard with real-time monitoring, challenge management, and intelligent AI interaction.

## 🌟 Project Highlights

### **Full-Featured Dashboard**
- Real-time game event monitoring via WebSocket
- Player state tracking (kills, deaths, inventory)
- Challenge system with rewards
- 115+ crafting recipe browser
- Interactive AI chat with command support
- Session analytics with LLM-powered insights

### **7 Main Pages**
1. **Dashboard** - Live overview and quick stats
2. **Live Logs** - Real-time event streaming
3. **Challenges** - Create and manage player challenges
4. **Inventory** - View all player items and equipment
5. **Crafting** - Browse recipes with search
6. **Chat AI** - Interact with AI agent
7. **Analytics** - Session analysis and reports

### **Professional Design**
- Steam-inspired dark theme
- Responsive layout (mobile to desktop)
- Smooth animations and transitions
- Color-coded status indicators
- Clean, intuitive UI

## 🚀 Quick Start

### Prerequisites
```bash
python 3.8+
FastAPI
WebSockets
Groq/Qwen/Llama LLM API key
```

### Installation
```bash
cd C:\Projects\Minecraft_AI_Agent
pip install -r requirements.txt
python main.py
```

### Access Dashboard
```
http://localhost:8000/
```

## 📊 Dashboard Pages

### Dashboard Home
Real-time overview with:
- Total events, kills, deaths count
- Active challenge status
- Recent events timeline
- AI agent connection status

### Live Logs
Features:
- WebSocket real-time streaming
- Level-based filtering (INFO, WARNING, ERROR)
- Auto-scroll toggle
- Clear logs button
- Color-coded log entries

### Challenges
Manage player challenges:
- Create challenges (kill or collect goals)
- Track progress with visual bars
- Claim rewards automatically
- View completion history
- Cancel active challenges

### Inventory
View player equipment:
- Main inventory grid with item counts
- Equipped armor pieces
- Hotbar (9 quick slots)
- Offhand slot
- Localized item names

### Crafting Recipes
Browse 115+ recipes:
- Search by name or ID
- Filter by category
- View recipe details
- Emoji indicators for quick identification
- Categories: Tools, Weapons, Armor, Blocks, Decoration, Redstone

### Chat AI
Interactive AI communication:
- Real-time messaging
- Built-in command support
- Tool-based actions:
  - Give items
  - Summon entities
  - Create challenges
  - Claim rewards
- Message history

### Analytics
Session analysis:
- Post-match tactical analysis
- Death statistics and timeline
- Health crisis tracking
- LLM-powered insights
- Session statistics summary

## 🔌 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Dashboard home |
| `/dashboard` | GET | Dashboard page |
| `/steam` | GET | Recipe viewer |
| `/api/logs/` | GET | Get logs |
| `/api/logs/ws` | WS | Real-time logs |
| `/api/player-state/` | GET | Player stats |
| `/api/player-state/inventory` | GET | Inventory |
| `/api/player-state/kills` | GET | Kill stats |
| `/api/challenges/` | GET/POST | Challenges |
| `/api/challenges/{id}/claim` | POST | Claim reward |
| `/api/challenges/{id}/cancel` | POST | Cancel challenge |
| `/api/rp/chat` | POST | Chat with AI |
| `/api/rp/` | GET | AI response |
| `/api/analytics/session_summary` | GET | Analysis |
| `/api/recipes` | GET | Recipe database |

## 🎨 Design System

### Colors
```css
Primary:        #1b2838 (Dark Navy)
Secondary:      #0c1419 (Darker Navy)
Accent:         #1e90ff (Bright Blue)
Text Primary:   #c7d5e0 (Light Gray)
Text Secondary: #8892a1 (Medium Gray)
Success:        #76c043 (Green)
Warning:        #f5a623 (Orange)
Danger:         #c41e3a (Red)
```

### Layout
- **Header**: Sticky navigation (60px height)
- **Sidebar**: Fixed left panel (240px width)
- **Main**: Responsive grid content area
- **Mobile**: Sidebar collapses, full-width content

### Breakpoints
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

## 📁 Project Structure

```
Minecraft_AI_Agent/
├── static/
│   ├── dashboard.html      # Main dashboard
│   ├── dashboard.css       # Styling
│   ├── dashboard.js        # Features
│   ├── steam.html          # Recipe viewer
│   ├── steam.css           # Recipe styling
│   └── steam.js            # Recipe features
├── api/
│   ├── logs.py             # Log streaming
│   ├── challenges.py       # Challenge system
│   ├── player_state.py     # Player tracking
│   ├── wiki.py             # Recipe search
│   ├── analytics.py        # Session analysis
│   ├── groq_client.py      # LLM integration
│   └── ...other APIs
├── data/
│   ├── minecraft_crafting_recipes.json  # 115+ recipes
│   ├── challenge_state.json             # Challenge data
│   └── ...other data
├── DASHBOARD.md            # Dashboard docs
├── STEAM_FRONTEND.md       # Recipe docs
├── README.md               # This file
└── main.py                 # FastAPI app
```

## 🎯 Key Features

### Real-time Monitoring
- WebSocket connection for live log streaming
- Instant player state updates
- Challenge progress tracking
- Connection status indicator

### Challenge Management
- Create challenges with custom goals
- Track progress automatically
- Claim rewards with one click
- View challenge history
- Cancel active challenges

### Intelligent AI Chat
- Tool-based command execution
- Natural language understanding
- Give items to players
- Summon entities
- Create challenges dynamically
- Claim rewards programmatically

### Comprehensive Analytics
- Session statistics compilation
- Death circumstances tracking
- Health crisis analysis
- Event timeline visualization
- LLM-powered insights

### Recipe Browser
- 115+ Minecraft crafting recipes
- Full-text search capability
- Category filtering
- 3x3 grid visualization
- Emoji quick identification

## 🛠️ Technical Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Real-time**: WebSockets
- **LLM**: Groq API integration
- **Database**: JSON files
- **Styling**: CSS Variables, Grid, Flexbox

## 📦 Dependencies

```
fastapi
uvicorn
websockets
pydantic
groq
```

See `requirements.txt` for complete list.

## 🔧 Configuration

### LLM Configuration
Set your LLM provider in `llm_config.json`:
```json
{
  "model_type": "groq",
  "api_key": "your-key-here",
  "model": "mixtral-8x7b-32768"
}
```

### Settings
Customize behavior in `settings.json`:
- Log retention
- Challenge rewards
- AI response parameters

## 🚀 Usage Examples

### Create Challenge
```
1. Go to Challenges page
2. Click "+ New Challenge"
3. Fill in details:
   - Title: "Creeper Hunter"
   - Goal: Kill 5 creepers
   - Reward: Diamond
4. Submit
```

### Monitor Game
```
1. Open Dashboard page
2. View real-time stats
3. Watch Live Logs
4. Check active challenge
5. See recent events
```

### Search Recipes
```
1. Go to Crafting page
2. Type "iron" in search
3. Select from results
4. View recipe details
```

### Chat with AI
```
1. Go to Chat page
2. Type: "give me diamond"
3. AI responds and gives item
4. Check inventory to confirm
```

## 📊 Performance Metrics

- **Dashboard Load**: < 500ms
- **Log Update**: Real-time (WebSocket)
- **API Response**: < 100ms
- **Crafting Search**: Instant

## 🔐 Security

- Input validation on all forms
- WebSocket connection validation
- XSS protection (HTML escaping)
- CORS headers configured
- No sensitive data in logs

## 🐛 Troubleshooting

### Dashboard Won't Load
```
1. Check server is running
2. Verify http://localhost:8000 is accessible
3. Clear browser cache
4. Check browser console for errors
```

### WebSocket Connection Fails
```
1. Ensure server is running
2. Check firewall settings
3. Verify no proxy interference
4. Check browser WebSocket support
```

### Logs Not Updating
```
1. Run game to generate events
2. Check /api/logs/ endpoint
3. Verify WebSocket connection
4. Check game client logs
```

### AI Chat Not Responding
```
1. Verify Groq API key is set
2. Check internet connection
3. Verify /api/rp/chat endpoint
4. Check console for errors
```

## 📚 Documentation

- **DASHBOARD.md** - Complete dashboard guide
- **STEAM_FRONTEND.md** - Recipe viewer guide
- **WIKI_CRAFTING.md** - Crafting system
- **README.md** - This file

## 🤝 Contributing

To add features:
1. Create new API endpoint in `api/`
2. Add page to dashboard HTML
3. Implement JavaScript handlers
4. Add CSS styling
5. Document in markdown files

## 📝 License

All code provided as-is for Minecraft AI Agent project.

## 🎮 Future Roadmap

- [ ] Player profile page
- [ ] Leaderboard system
- [ ] Achievement tracking
- [ ] Multi-player support
- [ ] Custom themes
- [ ] Data export (CSV, JSON)
- [ ] Replay functionality
- [ ] Voice commands
- [ ] Mobile app
- [ ] Cloud sync

## 📞 Support

For issues:
1. Check browser console
2. Verify server is running
3. Check API endpoints respond
4. Review documentation
5. Check game logs

---

**Version**: 1.0.0  
**Created**: 2024  
**Status**: Production Ready  

Made with ❤️ for Minecraft AI enthusiasts
