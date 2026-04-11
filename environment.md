# Python Environment Management Guide

This guide explains how to set up, manage, and maintain the Python virtual environment for this repository on Linux (Xubuntu/Ubuntu).

---

## 1. Initial Setup
To create a virtual environment inside the project folder, run:
```bash
python3 -m venv .venv
```
*Note: Using `.venv` as a name keeps the folder hidden in Linux.*

## 2. Activating the Environment
Before working on the project, you must activate the environment so the terminal uses the local Python interpreter and packages.

```bash
source .venv/bin/activate
```
Once activated, you will see `(.venv)` at the beginning of your command prompt.

## 3. Installing Dependencies
You can install packages individually:
```bash
pip install <package_name>
```
Or install everything required for this project at once:
```bash
pip install -r requirements.txt
```

## 4. Freezing Dependencies (requirements.txt)
If you install new libraries and want to save the changes so others can use them, "freeze" the current state:
```bash
pip freeze > requirements.txt
```

## 5. Renaming the Environment
Virtual environments contain hardcoded paths, so **you cannot simply rename the folder**. To "rename" it:
1. **Deactivate** the current one: `deactivate`
2. **Delete** the old folder: `rm -rf .old_venv_name`
3. **Create** a new one with the desired name: `python3 -m venv .new_name`
4. **Reinstall** dependencies: `source .new_name/bin/activate && pip install -r requirements.txt`

## 6. Deactivating and Cleaning Up
To stop using the environment and return to the system Python:
```bash
deactivate
```

---

## Quick Tips for Git
- **Never commit your environment folder**: Ensure your `.gitignore` file contains the name of your environment folder (e.g., `.venv/`).
- **Always update requirements**: Run `pip freeze > requirements.txt` before every `git commit` if you added new tools.