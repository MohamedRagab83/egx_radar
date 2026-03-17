@echo off
cd /d "d:\egx radar seprated"
".venv\Scripts\python.exe" run_3_backtests.py > bt_output.txt 2> bt_errors.txt
echo DONE > bt_done.txt
