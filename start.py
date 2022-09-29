import recruiter_app
import os

print("Welcome to hush hush recruiter cmd line tool")
if "exec_mode" not in os.environ:
    raise Exception("Enter the mode of execution")
mode = os.environ["exec_mode"]
print(f"Tool will run in {mode} mode")
recruiter_app.start(mode)
print("Execution completed successfully")
