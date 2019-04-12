import arcpy, csv, os, operator, os.path
#register the dialect for windows csv
csv.register_dialect("windcsv", lineterminator="\n")


class Toolbox(object):
	def __init__(self):
		"""Define the toolbox (the name of the toolbox is the name of the
		.pyt file)."""
		self.label = "ORGPTools"
		self.alias = "ORGP Script Tools"
		
		# List of tool classes associated with this toolbox
		self.tools = [gen6f3Map]

		
class gen6f3Map(object):
	"""tool that generates 6f3 maps for old projects"""
	def __init__(self):
		"""Define the tool (tool name is the name of the class)."""
		self.label = "Generate 6f3 map"
		self.description = "tool that generates 6f3 maps for closed projects"
		self.canRunInBackground = False
		
		#set constants here, describing the text contents of the elements
		self.templateMXDpath = "H:\gis\mapTemplates\XX-XXXXX 6(f)3.mxd"
		
		#set data library paths and field names for various datasets
		self.city = r"H:\gis\main\ORGPGISReplica.gdb\OGcities"
		self.parks = r"H:\gis\mapTemplates\FundedParks.lyr"
		self.grantPoint = "H:\gis\main\ORGPGISReplica.gdb\OGgrantPoints"
		self.projectBoundary = "H:\gis\main\ORGPGISReplica.gdb\OGsec6f3StateFed"
		self.projectBoundaryLayerFilePath = r"H:\gis\mapTemplates\Project Boundary.lyr"
		self.parkFundedField = "type"
		self.parkFundedFieldValue = "funded park"
		self.parkNameField = "currentNam"
		self.parkNumField = "parkNum"
		self.grantNumberField = "projectNum"
		self.parkManagmentField = "mgntOrg"
		self.parkCityField = "city"
		self.parkCountyField = "county"
		self.cityNameField = "city_name"
		self.parkPrevNamesField = "pastName"
		
		self.standardMapScales = [1000 , 2000 , 3000, 6000, 12000, 24000, 48000, 50000, 80000]
		
		
		
	def getParameterInfo(self):
		"""defines the tools parameters"""
		#Town name, Park name, or project number
		inputText = arcpy.Parameter(name="inputtext" ,
			displayName="Input Text, Please enter park name, park number, project number or city name",
			direction="Input",
			datatype="GPString",
			parameterType="Required")
		
		
		#output folder pdfs to go into
		outputFolder = arcpy.Parameter(name="outputFolder" ,
			displayName="Output Folder",
			direction="Ouput",
			datatype="DEFolder",
			parameterType="Required")
		
		
		#return the parameters to the tool
		return [inputText, outputFolder]
		
	def findPerfectScale(self, dataframe):
		"""find the perfect scale for the project boundary map"""
		
		#loop through all the standard scales
		for scale in self.standardMapScales:
			#if the standard scale is greater than the zoomed in map scale than use it
			#looping is occuring from smallest to largest scale
			if dataframe.scale < scale:
				dataframe.scale = scale
				return
	
	def findGraphicElements(self, mxd):
		"""finds the mxd graphic elements needed and returns them as a data dictionary"""
		
		#create a dictionary to hold the references to graphic elements need to be fille in
		elementsDic = {"Map Title" : "" , "Park Name" : "" , "Date" : "" , "Town County": "", "Owner" : "", "Draft" : ""}
		
		#loop through all the graphic elements to find the right ones
		for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
			if elm.name == "title":
				elementsDic["Map Title"] = elm
			if elm.name == "park name":
				elementsDic["Park Name"] = elm
			if elm.name == "date":
				elementsDic["Date"] = elm
			if elm.name == "town county":
				elementsDic["Town County"] = elm
			if elm.name == "owner":
				elementsDic["Owner"] = elm
			if elm.name == "draft":
				elementsDic["Draft"] = elm
				
		if elementsDic["Map Title"] == "":
			raise Exception
			
		if elementsDic["Park Name"] == "":
			raise Exception
			
		if elementsDic["Date"] == "":
			raise Exception
			
		if elementsDic["Town County"] == "":
			raise Exception
		
		if elementsDic["Owner"] == "":
			raise Exception
		
		
		
		#return the dictionary to the end user
		return elementsDic
		
	def cleanProjectNumbers(self, inputsList):
		"""transforms a list set into something with project numbers stripped of FY years and county apprevations"""
		pass
		
		
	def execute(self, parameters, messages):
		"""The source code of the tool."""
		
		#inputs from the tool user
		messages.AddMessage("Processing inputs")
		
		#split the string into its elements
		rawInputString = parameters[0].valueAsText
		
		#check to see if the string has a seperator character
		if "," in rawInputString:
			inputList = rawInputString.split(",")#if it does split the string along it
			if None in inputList:#remove any None values created by too many "," characters to no characters between them
				inputList.remove(None)#remove the None values
		else:#create a list if the value is only just one item
			inputList = [rawInputString.strip()]
		
		messages.AddMessage(inputList)
		#get the text value of the save folder
		saveFolder = parameters[1].valueAsText
		
		
		
		
		
		#loop through towns to find which ones are in the string
		messages.AddMessage("Searching for matching towns")
		involvedTowns = []#create list to store names of towns that are were named and exist
		
		#open cursor for the towns to loop through
		townCur = arcpy.da.SearchCursor(self.city, [self.cityNameField] )
		for row in townCur:
			#loop through all of the user inputs
			for inputElement in inputList:
				#check to see if the value of the town name matches the user input, strip out white space and make comparison not case sensitive
				if inputElement.replace("City of" , "").upper().strip() == row[0].upper():
					involvedTowns.append(row[0])#if they match add to the towns list
		
		del townCur#prevent schema locks
		messages.AddMessage(involvedTowns)#let user know that towns were varified
		
		'''Future feature search for county sponsors as well'''
		
		#loop through project numbers
		#if there are project numbers then find which parks they refer to
		messages.AddMessage("Searching for involved grants")
		involvedGrants = []#list to store park numbers generated from grants
		prjCur = arcpy.da.SearchCursor(self.grantPoint, [self.grantNumberField, self.parkNumField])#open cursor into the grants dataset
		for row in prjCur:
			#loop through input text
			for inputElement in inputList:
				#if the input text matches the grant number without whitespace and case insensitive then append to park numbers grant list
				if inputElement.upper().strip() == row[0].upper().strip():
					involvedGrants.append(row[1])
					
		del prjCur#delete to prevent schema locks
		messages.AddMessage(involvedGrants)
		
		#loop through parks
		messages.AddMessage("Looping through Parks")
		involvedParks = []#list that stores park numbers
		parkCur = arcpy.da.SearchCursor(self.parks, [self.parkNameField, self.parkNumField, self.parkManagmentField, self.parkPrevNamesField])#loop through parks dataset
		for row in parkCur:
			
			#check to see if a park number matches user inputs
			for inputElement in inputList:
				#compare without case sensitivity for park number
				if inputElement.upper().strip() == row[1].upper().strip():
					involvedParks.append(row[1])
			
				#check to see if the park name is a match
				if inputElement.upper().strip() == row[0].upper().strip():
					involvedParks.append(row[1])
					
				#check to see if any previous park names match
				#if the the field is blank or not, if its not check the contents
				if not (row[3] == None or row[3] == "" or row[3] == " " or row[3] == "NULL" or row[3] == "Null"):
					
					#if there are multiple previous parks then make a list and loop through them
					if "," in row[3]:
						for prevParkName in row[3].split(","):
							#if the previous park name and input element match then append to park number list
							if prevParkName.upper().strip() == inputElement.upper().strip():
								involvedParks.append(row[1])
					
					#if there is only one previous park name then compare it alone
					else:
						if row[3].upper().strip() == inputElement.upper().strip():
							involvedParks.append(row[1])
				
				
			#if there are involved towns then
			if len(involvedTowns) > 0:
				
				#check to see if the managment group field is filled out, if not then skip it
				if not (row[2] == None or row[2] == ""):
				
					#if there are towns, find their associated parks
					#check to see if any mentioned towns are managing parks
					for town in involvedTowns:
						#compare without whitespace and without the prefix of City of, also not case sensitive
						if town.upper().strip().replace("CITY OF " , "") == row[2].upper().strip().replace("CITY OF " , ""):
							involvedParks.append(row[1])#if matches append park number to list
			
		del parkCur#delete to prevent schema locks
		
		#generate a list of all three , remove redundant entries in the list for park numbers
		involvedParks = list(set(involvedParks + involvedGrants))
		
		#let the end user know how many parks were selected
		messages.AddMessage("The following parks were selected")
		for row in involvedParks:
			messages.AddMessage( "     " + row)
		
		#if no parks were selected then raise an error to indicate such, thus ending the script
		if len(involvedParks) == 0:
			raise Exception("unable to find parks, please enter a valid project number, city name, or park number")
		else:
			#if parks were selected then create the folder to place everything inside of
			os.makedirs(saveFolder)
		
		
		
		
		
		
		#will be used to determine zoom levels
		messages.AddMessage("making an overall parks layer")
		ParksLayerObject = arcpy.mapping.Layer(self.parks)
		
		
		#copy template for each park in list
		messages.AddMessage("making main template object")
		self.mxdTemplateObject = arcpy.mapping.MapDocument(self.templateMXDpath)
		
		#make a list of parks to loop through to generate a map set
		messages.AddMessage("starting to loop through park numbers")
		for parkNumber in involvedParks:
			
			#make a copy of the mxd according to the park number
			messages.AddMessage("making template copy mxd")
			localParkMXDPath = os.path.join(saveFolder, parkNumber + ".mxd")#save the document according to the park number
			self.mxdTemplateObject.saveACopy(localParkMXDPath)
			localParkMXD = arcpy.mapping.MapDocument(localParkMXDPath)
			
			#find all the graphic element object inside of the map document that we will need
			messages.AddMessage("Finding graphic elements")
			graphicElementsDic = self.findGraphicElements(localParkMXD)
			
			#get the main dataframe object of the template
			dataFrame = arcpy.mapping.ListDataFrames(localParkMXD)[0]
			
			#zoom each template to the parks extent by applying a definition query
			ParksLayerObject.definitionQuery = self.parkNumField + "=" + "'" + parkNumber + "'"
			#zoom the mxd to the def quiered layer
			dataFrame.extent = ParksLayerObject.getExtent()
			#correc the zoomed in map according to standerdized map scales
			self.findPerfectScale(dataFrame)
			
			
			#filling in all associated project numbers from the park inside of the title
			#search for all the grants associated with the park number
			grantCur = arcpy.da.SearchCursor(self.grantPoint, [self.grantNumberField], self.parkNumField + " =  '" + parkNumber + "'" )
			projectNumsString = ""
			
			#looping through grants on the park, turning them into a single string for use in the map document's title
			for row in grantCur:
				projectNumsString = projectNumsString + ", " + row[0]
			projectNumsString = projectNumsString[2:]#remove the strange starting characters created by the looping technique
			
			
			
			#spatial join and dissolve federal and state 6f3 boundary into a scratch layer for the map.
			#find information to fill into template
			#search the quired park layer for the park name, city, county info, LEAVE OWNER BLANK
			parkCur = arcpy.da.SearchCursor(ParksLayerObject, [self.parkNameField, self.parkCityField, self.parkCountyField, self.parkPrevNamesField])
			
			#variables needed for parks info in the map
			parkName = ""
			parkCity = ""
			parkCounty = ""
			parkPrevNames = ""
			
			#loop through to set the variables needed for the fill in info
			messages.AddMessage("finding info need to fill in graphic elements")
			for row in parkCur:
				parkName = row[0]
				parkCity = row[1]
				parkCounty = row[2]
				parkPrevNames = row[3]
			
			#if the park does not have any previous names then make the string empty, if not add a previous and parentheses to the string
			if parkPrevNames == None or parkPrevNames == "" or parkPrevNames == " " or len(parkPrevNames) == 0:
				parkPrevNames = ""
			else:
				parkPrevNames = "( Prev. " + parkPrevNames + ")"
			
			#set all of the fill in values for the differnt mxd text
			messages.AddMessage("Setting graphic element text")
			graphicElementsDic["Map Title"].text = projectNumsString + " Project Boundary Map"
			#check to see if the title with project numbers got too big
			if graphicElementsDic["Map Title"].elementWidth > 8:#wider than 8 inches
				graphicElementsDic["Map Title"].elementWidth = 8
			
			#check to see if the park name is longer than the page legnth.
			graphicElementsDic["Park Name"].text = parkName + parkPrevNames
			if graphicElementsDic["Park Name"].elementWidth > 8:#wider than 8 inches
				graphicElementsDic["Park Name"].elementWidth = 8
			
			graphicElementsDic["Date"].text = "Created: \n" + datetime.datetime.now().strftime("%m/%d/%Y")
			graphicElementsDic["Town County"].text = parkCity + "\n" + parkCounty + " County \n" + "Arkansas"
			graphicElementsDic["Draft"]. elementPositionX = -2.5
			
			#generate a new feature class by combining/Dissolving state and federal 6(f)3 boundaries that touch the park footprint
			messages.AddMessage("Making dissolve feature class")
			
			#make a layer object for 6f3 boundaires so it can hold a selection
			projectBoundaryLayerObject = arcpy.mapping.Layer(self.projectBoundary)
			arcpy.SelectLayerByLocation_management(projectBoundaryLayerObject, "INTERSECT", ParksLayerObject )#select 6f3 state and federal bounds touching selected park
			
			dissolvePath = os.path.join(saveFolder,  parkNumber + ".shp")
			arcpy.Dissolve_management(projectBoundaryLayerObject , dissolvePath , "", "" , "SINGLE_PART")
			#add this to mxd and apply using a layer file
			newBoundaryLayer = arcpy.mapping.Layer(dissolvePath)
			#apply a good symboligy to the layer for use
			arcpy.ApplySymbologyFromLayer_management (newBoundaryLayer, self.projectBoundaryLayerFilePath)
			newBoundaryLayer.name = "Project Boundary"
			
			#insert layer into the mxd
			arcpy.mapping.AddLayer(dataFrame , newBoundaryLayer , "TOP")
			
			#export to pdf in that folder
			messages.AddMessage("Exporting pdf")
			pdfPath = os.path.join(saveFolder, parkNumber + "- " + parkName + ".pdf")
			arcpy.mapping.ExportToPDF(localParkMXD, pdfPath)
			messages.AddMessage("saving map document")
			
			#save the mxd document and move on
			localParkMXD.save()
			
			
			
			
			
			
			'''optional future feature '''
			#loop through parcel data and associated lease and deed feature classes, see if information is in there
			#copy that info into the owner thing
			
			os.startfile(pdfPath)
		
		os.startfile(saveFolder)
			