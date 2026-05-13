# Dispatch

A cloud-native, serverless email marketing platform built on AWS.

## Stack

- **Frontend:** Next.js, TypeScript, Tailwind CSS, React
- **Backend:** Python 3.12, AWS Lambda, SQS, SES, DynamoDB, API Gateway
- **Infrastructure:** Terraform
- **AI:** Google Gemini (campaign generation)

## Project Structure

```
dispatch/
├── frontend/          # Next.js app
├── backend/           # Python Lambda functions
│   ├── lambdas/
│   │   ├── send_email/       # SES email dispatch
│   │   ├── track_event/      # Open/click/bounce tracking
│   │   ├── process_queue/    # SQS consumer
│   │   └── campaign_ai/      # Gemini AI generation
│   └── layers/common/        # Shared utilities
└── infrastructure/    # Terraform modules
```

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.12
- AWS CLI configured
- Terraform 1.5+
- Google Gemini API key

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### Backend (local testing)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Infrastructure

```bash
cd infrastructure/environments/dev
terraform init
terraform plan
terraform apply
```

## Environment Variables

See `.env.example` in each directory for required variables.
