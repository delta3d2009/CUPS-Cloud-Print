#    CUPS Cloudprint - Print via Google Cloud Print
#    Copyright (C) 2011 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import cups, urllib, logging, sys
sys.path.insert(0, ".")

from printer import Printer
from test_mockrequestor import MockRequestor

global requestors, printerItem

def setup_function(function):
    # setup mock requestors
    global requestors
    requestors = []

    # account without special chars
    mockRequestorInstance1 = MockRequestor()
    mockRequestorInstance1.setAccount('testaccount1')
    mockRequestorInstance1.printers = []
    requestors.append(mockRequestorInstance1)

    # with @ symbol
    mockRequestorInstance2 = MockRequestor()
    mockRequestorInstance2.setAccount('testaccount2@gmail.com')
    mockRequestorInstance2.printers = [ { 'name' : 'Save to Google Drive', 'id' : '__google__docs', 'capabilities' : [{ 'name' : 'ns1:Colors', 'type' : 'Feature' }] },  ]
    requestors.append(mockRequestorInstance2)

    # 1 letter
    mockRequestorInstance3 = MockRequestor()
    mockRequestorInstance3.setAccount('t')
    mockRequestorInstance3.printers = []
    requestors.append(mockRequestorInstance3)

    # instantiate printer item
    if function != test_instantiate:
        test_instantiate()

def teardown_function(function):
    global requestors
    requestors = None
    logging.shutdown()
    reload(logging)

def test_parseURI():
    global printerItem, requestors
    account, printerid = printerItem.parseURI("cloudprint://testaccount2%40gmail.com/testid")
    assert account == "testaccount2%40gmail.com"
    assert printerid == "testid"

def test_parseLegacyURI():
    global printerItem, requestors
    
    # 20140210 format
    account, printername, printerid, formatid = printerItem.parseLegacyURI("cloudprint://printername/testaccount2%40gmail.com/", requestors)
    assert formatid == printerItem.URIFormat20140210
    assert account == "testaccount2@gmail.com"
    assert printername == "printername"
    assert printerid == None
    
    # 20140307 format
    account, printername, printerid, formatid = printerItem.parseLegacyURI("cloudprint://printername/testaccount2%40gmail.com/testid", requestors)
    assert formatid == printerItem.URIFormat20140307
    assert account == "testaccount2@gmail.com"
    assert printername == "printername"
    assert printerid == "testid"
    
    # 20140308+ format
    account, printername, printerid, formatid = printerItem.parseLegacyURI("cloudprint://testaccount2%40gmail.com/testid", requestors)
    assert formatid == printerItem.URIFormatLatest
    assert account == "testaccount2@gmail.com"
    assert printerid == "testid"
    assert printername == None
    
    printerid, requestor = printerItem.getPrinterIDByDetails( "testaccount2@gmail.com", "printername", "testid" )
    assert printerid == "testid"
    assert isinstance(requestor, MockRequestor)
    assert requestor.getAccount() == 'testaccount2@gmail.com'

def test_getCUPSPrintersForAccount():
    global printerItem, requestors
    
    foundprinters, connection = printerItem.getCUPSPrintersForAccount(requestors[1].getAccount())
    assert foundprinters == []
    assert isinstance(connection, cups.Connection)
    
    # total printer
    totalPrinters = 0
    for requestor in requestors:
        totalPrinters+=len(requestor.printers)

    fullprintersforaccount = printerItem.getPrinters(True, requestors[1].getAccount())
    assert len(fullprintersforaccount) == len(requestors[1].printers)
    assert 'fulldetails' in fullprintersforaccount[0]
    assert len(fullprintersforaccount[0]['fulldetails']) > 0

    fullprinters = printerItem.getPrinters(True)
    assert len(fullprinters) == totalPrinters
    assert 'fulldetails' in fullprinters[0]
    assert len(fullprinters[0]['fulldetails']) > 0

    printers = printerItem.getPrinters()
    assert len(printers) == totalPrinters
    printer = printers[0]
    uri = printerItem.printerNameToUri(requestors[1].getAccount(), printer['id'])
    account, printerid = printerItem.parseURI(uri)
    printerId, requestor = printerItem.getPrinterIDByURI(uri)

    # get ppd
    ppdid = 'MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:'
    ppds = connection.getPPDs(ppd_device_id=ppdid)
    printerppdname, printerppd = ppds.popitem()

    # test add printer to cups
    assert printerItem.addPrinter( printer['name'], uri, connection, printerppdname) != None
    foundprinters, newconnection = printerItem.getCUPSPrintersForAccount(requestors[1].getAccount())
    # delete test printer
    connection.deletePrinter( printerItem.sanitizePrinterName(printer['name']) )
    
    assert isinstance(foundprinters, list)
    assert len(foundprinters) == 1
    assert isinstance(connection, cups.Connection)

def test_instantiate():
    global requestors, printerItem
    # verify adding single requestor works
    printerItem = Printer(requestors[0])
    assert printerItem.requestors[0] == requestors[0]
    assert len(printerItem.requestors) == 1

    # verify adding whole array of requestors works
    printerItem = Printer(requestors)
    assert printerItem.requestors == requestors
    assert len(printerItem.requestors) == len(requestors)

def test_getCapabilities():
    global printerItem, requestors
    foundprinters, connection = printerItem.getCUPSPrintersForAccount(requestors[1].getAccount())
    
    # total printer
    totalPrinters = 0
    for requestor in requestors:
        totalPrinters+=len(requestor.printers)

    fullprinters = printerItem.getPrinters(True)

    printers = printerItem.getPrinters()
    printer = printers[0]
    uri = printerItem.printerNameToUri(requestors[1].getAccount(), printer['id'])
    account, printerid = printerItem.parseURI(uri)
    printerId, requestor = printerItem.getPrinterIDByURI(uri)

    # get ppd
    ppdid = 'MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:'
    ppds = connection.getPPDs(ppd_device_id=ppdid)
    printerppdname, printerppd = ppds.popitem()

    # add test printer to cups
    assert printerItem.addPrinter( printer['name'], uri, connection, printerppdname) != None
    foundprinters, newconnection = printerItem.getCUPSPrintersForAccount(requestors[1].getAccount())
    
    emptyoptions = printerItem.getCapabilities( printerId, printerItem.sanitizePrinterName(printer['name']), "" )
    assert isinstance(emptyoptions, dict)
    assert isinstance(emptyoptions['capabilities'], list)
    assert len(emptyoptions['capabilities']) == 0
    
    # delete test printer
    connection.deletePrinter( printerItem.sanitizePrinterName(printer['name']) )

def test_GetPrinterIDByURIFails (  ):
    global printerItem, requestors

    # ensure invalid account returns None/None
    printerIdNoneTest , requestorNoneTest = printerItem.getPrinterIDByURI('cloudprint://testprinter/accountthatdoesntexist')
    assert printerIdNoneTest == None
    assert requestorNoneTest == None

    # ensure invalid printer on valid account returns None/None
    printerIdNoneTest , requestorNoneTest = printerItem.getPrinterIDByURI('cloudprint://testprinter/' + urllib.quote(requestors[0].getAccount()) )
    assert printerIdNoneTest == None
    assert requestorNoneTest == None

def test_addPrinterFails ( ) :
    global printerItem
    assert printerItem.addPrinter( '', '', '' ) == False

def test_findPrinterFails ( ) :
    global printerItem
    printerItem.requestor = requestors[0]
    assert printerItem.getPrinterDetails('dsah-sdhjsda-sd') == None

def test_invalidRequest ( ) :
    testMock = MockRequestor()
    assert testMock.doRequest('thisrequestisinvalid') == None

def test_internalName():
    global printerItem

    internalCapabilityTests = []

    # generate test cases for each reserved word
    #for word in printerItem.reservedCapabilityWords:
    #    internalCapabilityTests.append( { 'name' : word } )

    # load test file and try all those
    for filelineno, line in enumerate(open('testing/testfiles/capabilitylist')):
        internalCapabilityTests.append( { 'name' : line.decode("utf-8") } )

    for internalTest in internalCapabilityTests:
        assert printerItem.getInternalName( internalTest, 'capability' ) not in printerItem.reservedCapabilityWords
        assert ':' not in printerItem.getInternalName( internalTest, 'capability' )
        assert ' ' not in printerItem.getInternalName( internalTest, 'capability' )
        assert len(printerItem.getInternalName( internalTest, 'capability' )) <= 30
        assert len(printerItem.getInternalName( internalTest, 'capability' )) >= 1
        
    for internalTest in internalCapabilityTests:
        for capabilityName in ["psk:JobDuplexAllDocumentsContiguously", "other", "psk:PageOrientation"]:
            assert printerItem.getInternalName( internalTest, 'option', capabilityName ) not in printerItem.reservedCapabilityWords
            assert ':' not in printerItem.getInternalName( internalTest, 'option', capabilityName )
            assert ' ' not in printerItem.getInternalName( internalTest, 'option' )
            assert len(printerItem.getInternalName( internalTest, 'option', capabilityName )) <= 30
            assert len(printerItem.getInternalName( internalTest, 'option', capabilityName )) >= 1

def test_printers():
    global printerItem, requestors

    # test cups connection
    connection = cups.Connection()
    cupsprinters = connection.getPrinters()

    # total printer
    totalPrinters = 0
    for requestor in requestors:
        totalPrinters+=len(requestor.printers)

    fullprinters = printerItem.getPrinters(True)
    assert 'fulldetails' in fullprinters[0]

    printers = printerItem.getPrinters()
    assert 'fulldetails' not in printers[0]
    import re
    assert len(printers) == totalPrinters
    for printer in printers:

        # name
        assert isinstance(printer['name'], unicode)
        assert len(printer['name']) > 0

        # account
        assert isinstance(printer['account'], str)
        assert len(printer['account']) > 0

        # id
        assert isinstance(printer['id'], unicode)
        assert len(printer['id']) > 0

        # test encoding and decoding printer details to/from uri
        uritest = re.compile("cloudprint://(.*)/" + urllib.quote( printer['id']) )
        uri = printerItem.printerNameToUri(printer['account'], printer['id'])
        assert isinstance(uri, str) or isinstance(uri, unicode)
        assert len(uri) > 0
        assert uritest.match(uri) != None
        
        account, printerid = printerItem.parseURI(uri)
        assert isinstance(account, str)
        assert urllib.unquote(account) == printer['account']

        printerId, requestor = printerItem.getPrinterIDByURI(uri)
        assert isinstance(printerId, str)
        assert isinstance(requestor, MockRequestor)
        
        # get ppd
        ppdid = 'MFG:GOOGLE;DRV:GCP;CMD:POSTSCRIPT;MDL:'
        ppds = connection.getPPDs(ppd_device_id=ppdid)
        printerppdname, printerppd = ppds.popitem()

        # test add printer to cups
        assert printerItem.addPrinter( printer['name'], uri, connection, printerppdname) != None
        testprintername = printerItem.sanitizePrinterName(printer['name'])

        # test printer actually added to cups
        cupsPrinters = connection.getPrinters()
        found = False
        for cupsPrinter in cupsPrinters:
            if ( cupsPrinters[cupsPrinter]['printer-info'] == testprintername ):
                found = True
                break

        assert found == True

        # get details about printer
        printerItem.requestor = requestor
        printerdetails = printerItem.getPrinterDetails(printer['id'])
        assert printerdetails != None
        assert printerdetails['printers'][0] != None
        assert 'capabilities' in printerdetails['printers'][0]
        assert isinstance(printerdetails['printers'][0]['capabilities'], list)

        # test submitting job
        assert printerItem.submitJob(printerId, 'pdf', 'testing/testfiles/Test Page.pdf', 'Test Page', testprintername ) == True
        assert printerItem.submitJob(printerId, 'pdf', 'testing/testfiles/Test Page Doesnt Exist.pdf', 'Test Page', testprintername ) == False

        # test submitting job with no name
        assert printerItem.submitJob(printerId, 'pdf', 'testing/testfiles/Test Page.pdf', '', testprintername ) == True
        assert printerItem.submitJob(printerId, 'pdf', 'testing/testfiles/Test Page Doesnt Exist.pdf', '', testprintername ) == False

        # png
        assert printerItem.submitJob(printerId, 'png', 'testing/testfiles/Test Page.png', 'Test Page', testprintername ) == True
        assert printerItem.submitJob(printerId, 'png', 'testing/testfiles/Test Page Doesnt Exist.png', 'Test Page', testprintername ) == False

        # ps
        assert printerItem.submitJob(printerId, 'ps', 'testing/testfiles/Test Page.ps', 'Test Page', testprintername ) == False
        assert printerItem.submitJob(printerId, 'ps', 'testing/testfiles/Test Page Doesnt Exist.ps', 'Test Page', testprintername ) == False

        # test failure of print job
        assert printerItem.submitJob(printerId, 'pdf', 'testing/testfiles/Test Page.pdf', 'FAIL PAGE', testprintername ) == False

        # delete test printer
        connection.deletePrinter( testprintername )

def test_backendDescription():
    global printerItem
    import re
    backendtest = re.compile("^\w+ \w+ \"\w+\" \".+\"$")
    description = printerItem.getBackendDescription()
    assert isinstance(description, str)
    assert description.startswith('network')
    assert backendtest.match(description) != None

def test_getListDescription():
    global printerItem
    assert printerItem.getListDescription( { 'name' : 'Save to Google Drive', 'account' : 'test', 'id' : '__google__docs' } ) == 'Save to Google Drive - cloudprint://test/__google__docs - test'
    assert printerItem.getListDescription( { 'name' : 'Save to Google Drive', 'displayName' : 'Save to Google Drive 2', 'account' : 'test', 'id' : '__google__docs' } ) == 'Save to Google Drive 2 - cloudprint://test/__google__docs - test'
    
def test_():
    global printerItem
    assert printerItem.getBackendDescriptionForPrinter( { 'name' : 'Save to Google Docs', 'account' : 'test', 'id' : '__google__docs' } ) == 'network cloudprint://test/__google__docs "Save to Google Docs" "Google Cloud Print" "MFG:Google;MDL:Cloud Print;DES:GoogleCloudPrint;"'