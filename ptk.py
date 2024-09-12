import sys

PATH_TO_PTK_PYTHON = r"C:\Program Files (x86)\Deltares\Probabilistic Toolkit\bin\Python"
PATH_TO_PROJECT_TKX = r"C:\Users\Public\Documents\Deltares\Probabilistic Toolkit\Examples\Piping\piping-reliability.tkx"

if not PATH_TO_PTK_PYTHON in sys.path:
    sys.path.insert(0, PATH_TO_PTK_PYTHON)

import toolkit_model as ptk

toolkit = ptk.ToolKit()


project = toolkit.load(PATH_TO_PROJECT_TKX)
messages = project.validate()

if len(messages) == 0:
    print("Project loaded succesfully")
    # project.run()
else:
    print(messages)

# toolkit.save(".tkx")
