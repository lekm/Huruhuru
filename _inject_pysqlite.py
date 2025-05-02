# _inject_pysqlite.py
import sys

try:
    # Try importing the binary version first
    __import__("pysqlite3")
    # Replace the standard sqlite3 module reference in sys.modules
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
    print("Successfully injected pysqlite3 as sqlite3.")
except ImportError:
    print("pysqlite3 not found, attempting to use standard sqlite3.")
    # If pysqlite3 isn't found, we just proceed hoping standard sqlite3 works (though it might fail later)
    pass 