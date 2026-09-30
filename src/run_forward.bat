@echo off
cd /d "C:\Users\youss\OneDrive\Documents\Queen Research\src"
echo ==== %date% %time% >> "..\out\forward_run.log"
"C:\Python314\python.exe" score_forward.py >> "..\out\forward_run.log" 2>&1
