# Storm Cases - Development Guide

## Project Overview
Storm Cases is a comprehensive Telegram Mini App for case opening, item trading, and social interaction with full admin panel functionality.

## Development Setup

### Prerequisites
- Node.js 18+
- PostgreSQL 12+
- Redis (optional)
- Telegram Bot Token

### Quick Start

1. **Backend Setup:**
```bash
cd storm-cases/backend
npm install
cp .env.example .env  # Configure your environment variables
npm run prisma:generate
npm run prisma:migrate
npm run prisma:seed
npm run dev
```

2. **Frontend Setup:**
```bash
cd storm-cases/frontend
npm install
npm run dev
```

### Environment Variables

Key variables in `backend/.env`:
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - Secret for JWT tokens
- `ADMIN_PASSWORD` - Password for admin panel access
- `MINI_APP_URL` - URL for Mini App (http://localhost:5173 for dev)

## Architecture

### Backend Structure
- **Express.js** - Web framework
- **Prisma** - ORM for database operations
- **Socket.io** - Real-time communication for chat
- **JWT** - Authentication
- **node-telegram-bot-api** - Telegram bot integration

### Frontend Structure
- **React 19** - UI framework
- **Vite** - Build tool
- **React Router** - Navigation
- **TanStack Query** - Data fetching
- **Socket.io Client** - Real-time communication
- **Axios** - HTTP client

## Database Schema

Key models:
- **User** - User accounts with levels, experience, balances
- **Case** - Different rarity cases with items
- **Item** - Individual items with crafting and upgrade options
- **InventoryItem** - User's inventory
- **MarketListing** - Market listings and auctions
- **ChatMessage** - Chat messages
- **SupportTicket** - Support system
- **ActivityLog** - User activity tracking

## API Endpoints

### Public Routes
- `/api/auth/*` - Authentication
- `/api/users/*` - User management
- `/api/cases/*` - Case operations
- `/api/inventory/*` - Inventory management
- `/api/market/*` - Market operations
- `/api/chat/*` - Chat functionality
- `/api/support/*` - Support tickets

### Admin Routes (require admin token)
- `/api/admin/users/*` - User management
- `/api/admin/logs/*` - Activity logs
- `/api/admin/support/*` - Support management
- `/api/admin/economy/*` - Economy management
- `/api/admin/analytics/*` - Analytics
- `/api/admin/moderation/*` - Moderation tools

## Development Commands

### Backend
```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run prisma:generate # Generate Prisma Client
npm run prisma:migrate   # Run database migrations
npm run prisma:seed      # Seed database with test data
```

### Frontend
```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
```

## Testing

### Backend Testing
- Integration tests for API endpoints
- Database operation tests
- Telegram bot webhook tests

### Frontend Testing
- Component tests with React Testing Library
- E2E tests with Playwright (optional)

## Deployment

### Backend Deployment
1. Set up PostgreSQL database
2. Configure environment variables
3. Run migrations: `npm run prisma:migrate`
4. Seed database: `npm run prisma:seed`
5. Build: `npm run build`
6. Start: `npm start`

### Frontend Deployment
1. Build: `npm run build`
2. Deploy `dist/` folder to static hosting
3. Update `MINI_APP_URL` in backend `.env`

### Telegram Bot Setup
1. Set webhook: `curl -F "url=https://your-domain.com/webhook" https://api.telegram.org/bot<TOKEN>/setWebhook`
2. Configure webhook URL in `.env`

## Troubleshooting

### Common Issues

**Database Connection Error:**
- Check `DATABASE_URL` in `.env`
- Ensure PostgreSQL is running
- Verify database exists

**Telegram Bot Not Responding:**
- Verify bot token is correct
- Check webhook is set correctly
- Ensure bot has necessary permissions

**Frontend Build Errors:**
- Clear node_modules and reinstall
- Check TypeScript types
- Verify all dependencies are installed

**Socket.io Connection Issues:**
- Check CORS settings
- Verify socket server is running
- Ensure correct URL in frontend

## Admin Panel Access

1. Open Mini App
2. Go to Settings
3. Navigate to Admin Panel tab
4. Enter admin password (from `ADMIN_PASSWORD` env var)
5. Access full admin functionality

## Feature Extensions

### Adding New Case Rarity
1. Update `Rarity` enum in `prisma/schema.prisma`
2. Add rarity colors in frontend CSS
3. Update case creation logic

### Adding New Currency
1. Update `Currency` enum in schema
2. Add currency conversion rates
3. Update UI to display new currency

### Custom Chat Commands
1. Add command handlers in `telegramBot.ts`
2. Create corresponding API endpoints
3. Update frontend to handle commands

## Performance Optimization

### Database
- Use connection pooling
- Add indexes for frequently queried fields
- Implement caching with Redis

### Frontend
- Implement code splitting
- Add image optimization
- Use lazy loading for components

### API
- Add rate limiting
- Implement request caching
- Use pagination for large datasets

## Security Considerations

- Always validate user input
- Use parameterized queries
- Implement rate limiting
- Secure admin endpoints
- Validate JWT tokens properly
- Sanitize chat messages
- Implement CSRF protection

## Monitoring and Logging

- Implement structured logging
- Set up error tracking (Sentry, etc.)
- Monitor database performance
- Track API response times
- Monitor socket connections

## Contributing

1. Follow existing code style
2. Add tests for new features
3. Update documentation
4. Use conventional commits
5. Create pull requests for review

## License

MIT License - See LICENSE file for details