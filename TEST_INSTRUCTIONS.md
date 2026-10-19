# LearnLoop Testing Instructions

## 1. Install Locally
\\\ash
pip install -e .
\\\

## 2. Start Dashboard
\\\ash
# Terminal 1
python -m learnloop.dashboard
# Access: http://localhost:8765
\\\

## 3. Test with Your Projects
\\\ash
cd your-project
learnloop init
# Work with AI, make commits
learnloop briefing  # See what changed
\\\

## 4. Test HTTP Deployment
\\\ash
pip install -r requirements_http.txt
python learnloop_http.py
# Access: http://localhost:8000
\\\

## Key Features to Test:
- ? Git commit tracking
- ? Dashboard insights
- ? Knowledge item management
- ? Session briefings
- ? HTTP/SSE endpoints

## When Ready for Production:
1. Used on 2-3 real projects
2. HTTP deployment tested
3. Performance acceptable
4. Provides meaningful learning insights

Happy testing! ??
