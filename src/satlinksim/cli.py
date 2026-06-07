import sys
import os
from streamlit.web import cli as stcli

def main():
    # Find the path to app.py relative to this file
    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    sys.argv = ["streamlit", "run", app_path] + sys.argv[1:]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
