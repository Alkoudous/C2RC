<!-- 5. ANALYS OF A RECONSTITUTION ---------------------------------------------------->
<a name="Automated Evaluation"></a>
# <strong style="color:brown"> **INSTALLATION** </strong> 
<!------------------------------------------------------------------------------------->
 	
### 1. Pre-requisites 

#### 1.1 Pycharm IDE
	https://www.jetbrains.com/products/compare/?product=pycharm&product=pycharm-ce
	
#### 1.2 Conda Package-Manager
	https://conda.io/projects/conda/en/latest/user-guide/getting-started.html
	
#### 1.3 Additional Libraries
	REQUIREMENTS		: pip install pipreqs
				  pipreqs /path/to/project
	FLASK			: pip install flask
	RDFLIB			: pip install rdflib
	DATE UTIL		: pip install python_dateutil
	GRAPH-TOOL		: conda install -c conda-forge graph-tool
	
### 2. C2RC Installation
	 - In Pycharm, create a new project "C2RC" using CONDA as your new environment. 
	 - Once created, add the src folder to the C2RC folder.
   	 - Open src/main.py in pycharm.
   	 - Right click it and run to get the server running.
   	 - The UI can then be found at http://127.0.0.1:5000.
