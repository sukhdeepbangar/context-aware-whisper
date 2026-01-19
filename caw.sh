#!/bin/bash
# Context-Aware Whisper management script

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

case "$1" in
    start)
        echo "Starting Context-Aware Whisper..."
        source venv/bin/activate
        nohup python main.py > context-aware-whisper.log 2>&1 &
        PID=$!
        echo $PID > context-aware-whisper.pid
        echo "Context-Aware Whisper started with PID: $PID"
        ;;
    stop)
        if [ -f context-aware-whisper.pid ]; then
            PID=$(cat context-aware-whisper.pid)
            echo "Stopping Context-Aware Whisper (PID: $PID)..."
            kill $PID 2>/dev/null && echo "Stopped" || echo "Already stopped"
            rm context-aware-whisper.pid
        else
            echo "No PID file found. Trying pkill..."
            pkill -f "python main.py"
        fi
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        if [ -f context-aware-whisper.pid ]; then
            PID=$(cat context-aware-whisper.pid)
            if ps -p $PID > /dev/null; then
                echo "Context-Aware Whisper is running (PID: $PID)"
            else
                echo "PID file exists but process is not running"
            fi
        else
            echo "Context-Aware Whisper is not running"
        fi
        ;;
    logs)
        tail -f context-aware-whisper.log
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
