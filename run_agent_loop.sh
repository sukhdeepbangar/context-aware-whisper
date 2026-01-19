#!/bin/bash

# Agent loop script - runs Claude agent with prompt.md, waits for completion, repeats

PROMPT_FILE="prompt.md"
SESSION_NAME="claude-agent"
LOG_FILE="agent_loop.log"

# Read the prompt
PROMPT=$(cat "$PROMPT_FILE")

echo "$(date): Starting agent loop" >> "$LOG_FILE"

while true; do
    echo "$(date): Starting new agent run..." >> "$LOG_FILE"

    # Kill any existing session with same name
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null

    # Create new tmux session and run claude with the prompt
    # Using --dangerously-skip-permissions to run without prompts
    tmux new-session -d -s "$SESSION_NAME" "cd /Users/sukhdeepsingh/projects/ClaudeProjects/context-aware-whisper && claude --dangerously-skip-permissions -p \"$PROMPT\" 2>&1 | tee -a agent_run.log; echo 'AGENT_COMPLETE' >> agent_status.txt"

    echo "$(date): Agent started in tmux session '$SESSION_NAME'" >> "$LOG_FILE"

    # Remove old status file
    rm -f agent_status.txt

    # Wait for agent to complete by checking for the completion marker
    while true; do
        if [ -f "agent_status.txt" ] && grep -q "AGENT_COMPLETE" agent_status.txt; then
            echo "$(date): Agent completed" >> "$LOG_FILE"
            break
        fi

        # Also check if tmux session is still running
        if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
            echo "$(date): Tmux session ended" >> "$LOG_FILE"
            break
        fi

        sleep 10
    done

    # Kill the session
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null
    rm -f agent_status.txt

    echo "$(date): Sleeping before next run..." >> "$LOG_FILE"
    sleep 5

    echo "$(date): Starting next iteration..." >> "$LOG_FILE"
done
