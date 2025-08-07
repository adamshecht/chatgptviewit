# BrightStone Property Monitoring System

A comprehensive property monitoring and alert system that tracks municipal council meetings and documents for real estate development opportunities.

## 🏗️ Architecture

### Backend (FastAPI + PostgreSQL)
- **FastAPI**: Modern Python web framework for high-performance APIs
- **PostgreSQL**: Robust relational database with optimized schema
- **NeonDB**: Cloud-hosted PostgreSQL for scalability
- **JWT Authentication**: Secure token-based authentication
- **Async Processing**: Non-blocking database operations

### Frontend (Next.js + React)
- **Next.js 15**: React framework with App Router
- **TypeScript**: Type-safe JavaScript development
- **Auth0 Integration**: Enterprise-grade authentication
- **Tailwind CSS**: Utility-first CSS framework
- **Responsive Design**: Mobile-first UI/UX

## 🚀 Features

### Core Functionality
- **Property Management**: Track properties with detailed metadata
- **Document Monitoring**: Automated council document ingestion
- **Alert System**: Real-time notifications for relevant documents
- **Multi-tenant**: Company-specific data isolation
- **Municipality Support**: Multiple city council feeds

### Advanced Features
- **AI Analysis**: OpenAI-powered document analysis
- **Email Notifications**: Automated alert delivery
- **Audit Trails**: Complete processing history
- **Performance Optimization**: Strategic database indexing
- **Data Integrity**: Comprehensive constraints and validations

## 📊 Database Schema

### Optimized Multi-tenant Architecture
- **Single Document Pipeline**: Documents stored once, shared across tenants
- **Company Isolation**: Secure data separation
- **Performance Indexes**: 33 strategic indexes for fast queries
- **JSONB Support**: Efficient JSON data storage with GIN indexes
- **Data Validation**: Comprehensive check constraints

### Key Tables
- `companies`: Company definitions and configurations
- `properties`: Monitored properties with metadata
- `municipalities`: City council feed configurations
- `meetings`: Council meeting records
- `documents`: Council documents with processing status
- `alerts`: Generated notifications with relevance scoring
- `audit_trails`: Processing history and analytics
- `users`: System users with role-based access

## 🛠️ Setup Instructions

### Prerequisites
- Node.js 18+ and npm
- Python 3.9+ and pip
- PostgreSQL database (NeonDB recommended)
- Auth0 account for authentication

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd BrightStone_Script
```

### 2. Backend Setup
```bash
cd api
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database and Auth0 credentials
```

### 3. Frontend Setup
```bash
cd web
npm install
cp .env.local.example .env.local
# Edit .env.local with your Auth0 credentials
```

### 4. Database Setup
```bash
cd migrations
python3 apply_migration.py
```

### 5. Start Services
```bash
# From project root
./start.sh
```

## 🔧 Environment Variables

### Backend (.env)
```env
DATABASE_URL=postgresql://user:pass@host/db
JWT_SECRET_KEY=your-secret-key
DEV_MODE=true
```

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret
AUTH0_CLIENT_ID=your-auth0-client-id
AUTH0_CLIENT_SECRET=your-auth0-client-secret
AUTH0_DOMAIN=your-auth0-domain
AUTH0_ISSUER=https://your-auth0-domain/
```

## 🗄️ Database Migrations

### Applied Migrations
1. **001_single_document_pipeline**: Initial schema with single-copy document architecture
2. **002_schema_optimizations**: Performance indexes and data integrity constraints
3. **003_final_optimizations**: JSONB optimization and final performance tuning

### Migration Commands
```bash
cd migrations
python3 apply_migration.py
python3 verify_migration.py
```

## 🔍 API Endpoints

### Authentication
- `POST /api/auth/login` - User authentication
- `POST /api/auth/refresh` - Token refresh
- `GET /api/auth/me` - Current user info

### Properties
- `GET /api/properties/` - List properties
- `POST /api/properties/` - Create property
- `PUT /api/properties/{id}` - Update property
- `DELETE /api/properties/{id}` - Delete property

### Alerts
- `GET /api/alerts/` - List alerts
- `PUT /api/alerts/{id}` - Update alert status
- `GET /api/alerts/{id}/comments` - Alert comments

### Documents
- `GET /api/documents/` - List documents
- `GET /api/documents/{id}` - Document details
- `PUT /api/documents/{id}/status` - Update processing status

## 🎯 Key Optimizations

### Database Performance
- **GIN Indexes**: 5 JSONB indexes for efficient JSON queries
- **Composite Indexes**: Strategic multi-column indexes
- **Unique Constraints**: 11 data integrity constraints
- **Foreign Keys**: 19 relationship constraints with CASCADE rules

### Application Performance
- **Connection Pooling**: Optimized database connections
- **Async Operations**: Non-blocking I/O operations
- **Caching**: Strategic data caching
- **Compression**: Optimized data transfer

### Security
- **JWT Tokens**: Secure authentication
- **CORS Configuration**: Proper cross-origin handling
- **Input Validation**: Comprehensive data validation
- **SQL Injection Protection**: Parameterized queries

## 📈 Monitoring & Analytics

### Audit Trails
- Document processing history
- Alert generation tracking
- Performance metrics
- Error logging

### Key Metrics
- Documents processed per day
- Alert generation rate
- Processing time averages
- Error rates and types

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For technical support or questions:
- Check the documentation in `/docs`
- Review the migration logs
- Contact the development team

---

**Built with ❤️ for BrightStone Property Management**
