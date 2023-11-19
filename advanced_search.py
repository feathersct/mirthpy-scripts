#!/usr/bin/python3
import urllib3
from mirthpy.mirthService import *
from mirthpy.connectors import *
from mirthpy.transformers import *
from mirthpy.filters import *

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#region Config Values
instances = []
property = ''   #TODO: Add your search property (anything in the Supporting Variables region)
value = ''      #TODO: Add your search value
enabledFlag = True  # Just get enabled channels, destinations, etc.
exactMatch = True   # Get exact match or partial matches
user = ''       #TODO: Add your username
passw = ''      #TODO: Add your password
#endregion

#region Supporting Variables
FTP_USER = "FTP User"
IP = "IP"
PORT = "Port"
JAVASCRIPT = "JavaScript"
CONTEXTPATH = "Context Path"
URL = "URL" #SFTP, Database Reader, Not JavaScript (note that some add a / to the url) 
RULEBUILDER_FIELD = "Filter_RuleBuilderField"
RULEBUILDER_VALUE = "Filter_RuleBuilderValue"
MAPPER_VAR = "Transformer_Mapper_Variable"
MAPPER_MAP = "Transformer_Mapper_Mapping"
MAPPER_DEFVAL = "Transformer_Mapper_Default_Value"
FILE_NAME = "Naming Convention"
CHANNEL = "Channel ID"

# Headers to display 
displayHeaders = {
    PORT: ["Channel Name", "Source or Destination", "Destination Name", "Property"],
    IP: ["Channel Name", "Source Or Destination", "Destination Name", "Property"],
    JAVASCRIPT: ["Channel","Location","Line #"],
    CONTEXTPATH: ["Channel Name", "Source or Destination", "Destination Name", "Property"],
    URL: ["Channel Name", "Source or Destination", "Destination Name", "Property"],
    RULEBUILDER_FIELD: ["Channel Name", "Source or Destination", "Destination Name", "Filter #"],
    RULEBUILDER_VALUE: ["Channel Name", "Source or Destination", "Destination Name", "Filter #"],
    MAPPER_VAR: ["Channel Name", "Source or Destination", "Destination Name", "Transformer #"],
    MAPPER_MAP: ["Channel Name", "Source or Destination", "Destination Name", "Transformer #"],
    MAPPER_DEFVAL: ["Channel Name", "Source or Destination", "Destination Name", "Transformer #"],
    FTP_USER: ["Channel Name", "Source or Destination", "Destination Name"],
    FILE_NAME: ["Channel Name", "Source or Destination", "Destination Name"],
    CHANNEL: ["Channel Name", "Source or Destination", "Destination Name"]
}

# terms to look for in the channels
searchTerms = {
    PORT: ["port"],
    IP: ["address", "host", "ip"],
    JAVASCRIPT: ["script"],
    CONTEXTPATH: ["contextPath"],
    URL: ["host", "wsdlUrl", "locationURI", "url"],
    RULEBUILDER_FIELD: ["field"],
    RULEBUILDER_VALUE: ["values"],
    MAPPER_VAR: ["variable"],
    MAPPER_MAP: ["mapping"],
    MAPPER_DEFVAL: ["defaultValue"],
    FTP_USER: ["username"],
    FILE_NAME: ["outputPattern"],
    CHANNEL: ['channelId']
}
#endregion

#region Supporting Functions
def getPropertiesThatMatch(propsToMatch, valueToMatch, properties, exactMatch = True):
    ret = [] # the specific properties matched in the object
    props = [prop for prop in dir(properties) if any(ptm.lower() in prop.lower() for ptm in propsToMatch)]
    for prop in props:
        # get the value of the property
        value = getattr(properties, prop)

        # turn the string into lower case version
        if type(value) == str:
            value = value.lower()

        if exactMatch:
            if type(value) == list:
                for v in value:
                    if v.lower() == valueToMatch.lower():
                        ret.append(prop)
            elif value == valueToMatch:
                ret.append(prop)
            
        else:
            if type(value) == list:
                for v in value:
                    if valueToMatch.lower() in v.lower():
                        ret.append(prop)
            elif value is not None:
                if valueToMatch.lower() in value.lower():
                    ret.append(prop)
    return ret

def checkScriptForMatch(script, searchValue):
    lineNumbers = []
    if script is not None:
        if searchValue in script.lower():
            lineNumbers = [str(i + 1) for i, s in enumerate(script.split('\n')) if searchValue in s.lower()]

    return lineNumbers

def checkForJavascriptMatch(channel, valueToMatch):
    scriptsWithFunction = []

    if type(channel.sourceConnector.properties) == JavaScriptReceiverProperties:
        lineNums = checkScriptForMatch(channel.sourceConnector.properties.script, valueToMatch)
        for lineNum in lineNums:
            scriptsWithFunction.append((channel.name, f'sourceConnector', lineNum))

    # for each source transformer
    for t in channel.sourceConnector.transformer.elements:
        if type(t) == JavaScriptStep:
            lineNums = checkScriptForMatch(t.script, valueToMatch)
            for lineNum in lineNums:
                scriptsWithFunction.append((channel.name, f'sourceConnector - transformer: {t.name}', lineNum))

    # for each source filter
    for t in channel.sourceConnector.filter.elements:
        if type(t) == JavaScriptRule:
            lineNums = checkScriptForMatch(t.script, valueToMatch)
            for lineNum in lineNums:
                scriptsWithFunction.append((channel.name, f'sourceConnector - filter: {t.name}', lineNum))

    # for each destination transformer
    for t in channel.destinationConnectors:
        if type(t.properties) == JavaScriptDispatcherProperties:
            lineNums = checkScriptForMatch(t.properties.script, valueToMatch)
            for lineNum in lineNums:
                scriptsWithFunction.append((channel.name, f'destinationConnector: {t.name}', lineNum))

        # destination transformer
        for e in t.transformer.elements:
            if type(e) == JavaScriptStep:
                lineNums = checkScriptForMatch(e.script, valueToMatch)
                for lineNum in lineNums:
                    scriptsWithFunction.append((channel.name, f'destinationConnector: {t.name} - transformer: {e.name}', lineNum))

        # destination filter
        for e in t.filter.elements:
            if type(e) == JavaScriptRule:
                lineNums = checkScriptForMatch(e.script, valueToMatch)
                for lineNum in lineNums:
                    scriptsWithFunction.append((channel.name, f'destinationConnector: {t.name} - filter: {e.name}', lineNum))
    return scriptsWithFunction
#endregion

# Main Search Function
def search(instance, username, password, searchProperty, searchValue, onlyEnabledFlag, exactTerm):
    # Convert Fields
    searchValue = searchValue.lower()
    exactTerm = exactTerm == "True"
    onlyEnabledFlag = onlyEnabledFlag == "True"

    ret = []

    # if not an included search term
    if searchProperty not in searchTerms.keys():
        searchTerms[searchProperty] = [searchProperty.lower()]


    # Open the Mirth Service with config
    service = MirthService(instance=instance, username=username, password=password)
    service.open()

    channels = service.getChannels()

    for channel in channels.channels:
        # skip disabled channels if user wants
        if onlyEnabledFlag:
            if channel.exportData.metadata.enabled == "false":
                continue

        # search JavaScript
        if searchProperty == JAVASCRIPT:
            for fi in checkForJavascriptMatch(channel, searchValue):
                ret.append(fi)
            continue

        # Check Source Connector
        if hasattr(channel.sourceConnector.properties, 'listenerConnectorProperties'):
            matchedProps = getPropertiesThatMatch(searchTerms[searchProperty], searchValue, channel.sourceConnector.properties.listenerConnectorProperties, exactTerm)
            for prop in matchedProps:
                ret.append((channel.name, 'Source', '', prop))
        
        # generic search in properties
        matchedProps = getPropertiesThatMatch(searchTerms[searchProperty], searchValue, channel.sourceConnector.properties, exactTerm)
        for prop in matchedProps:
            ret.append((channel.name, 'Source', '', prop))

        # Check Filters
        for element in channel.sourceConnector.filter.elements:
            if not onlyEnabledFlag or (onlyEnabledFlag and element.enabled == 'true'):
                matchedProps = getPropertiesThatMatch(searchTerms[searchProperty], searchValue, element, exactTerm)
                for prop in matchedProps:
                    ret.append((channel.name, 'Source', '', element.sequenceNumber))
        
        # Check Transformers
        for element in channel.sourceConnector.transformer.elements:
            if not onlyEnabledFlag or (onlyEnabledFlag and element.enabled == 'true'):
                matchedProps = getPropertiesThatMatch(searchTerms[searchProperty], searchValue, element, exactTerm)
                for prop in matchedProps:
                    ret.append((channel.name, 'Source', '', element.sequenceNumber))
        
        # Check Outbound Destination Connectors
        for destination in channel.destinationConnectors:
            if onlyEnabledFlag:
                if destination.enabled == "false":
                    continue

            matchedProps = getPropertiesThatMatch(searchTerms[searchProperty],searchValue,destination.properties, exactTerm)
            for prop in matchedProps:
                ret.append((channel.name, 'Destination', destination.name, prop))

            # Check Filters
            for element in destination.filter.elements:
                if not onlyEnabledFlag or (onlyEnabledFlag and element.enabled == 'true'):
                    matchedProps = getPropertiesThatMatch(searchTerms[searchProperty], searchValue, element, exactTerm)
                    for prop in matchedProps:
                        ret.append((channel.name, 'Destination', destination.name, element.sequenceNumber))
            
            # Check Transformers
            for element in destination.transformer.elements:
                if not onlyEnabledFlag or (onlyEnabledFlag and element.enabled == 'true'):
                    matchedProps = getPropertiesThatMatch(searchTerms[searchProperty], searchValue, element, exactTerm)
                    for prop in matchedProps:
                        ret.append((channel.name, 'Destination', destination.name, element.sequenceNumber))
    service.close()

    return ret

if __name__ == "__main__":
    print(','.join(displayHeaders[property]))
    for i in instances:
        foundItems = search(i, user, passw, property, value, enabledFlag, exactMatch)
        
        # Display Values to User
        for f in foundItems:
            print(','.join(f))



