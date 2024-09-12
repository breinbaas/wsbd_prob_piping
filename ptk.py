import sys

PATH_TO_PTK_PYTHON = r"C:\Program Files (x86)\Deltares\Probabilistic Toolkit\bin\Python"

if not PATH_TO_PTK_PYTHON in sys.path:
    sys.path.insert(0, PATH_TO_PTK_PYTHON)

from toolkit_model import *

toolkit = ToolKit()


# project = toolkit.load("")
# messages = project.validate()

# if len(messages) == 0:
#     project.run()

# toolkit.save(".tkx")
