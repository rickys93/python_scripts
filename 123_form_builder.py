import urllib2
import httplib
import json
import requests
import time
import datetime
from requests.auth import HTTPBasicAuth
from database2 import *
import string
import os
from dropbox.files import WriteMode




destination_folder = '123FormBuilder'
lstExt = ['jpg', 'png', 'jpeg', 'pdf']


fieldIds = {u'63267941-1':'firstName',
        u'63267941-2':'lastName',
        u'63267942':'email',
        u'63296332':'lbcRef',
        u'63272301':'dob',
        u'63272323-1':'streetAddress',
        u'63272323-3':'city',
        u'63272323-5':'postalCode',
        u'63272323-6':'country',
        u'63267947_0':'terms',
        u'63267948_0':'privacy',
        u'63270172':'bank_statement',
        u'63270210':'selfie',
        u'63270222':'note'}	


fieldsIdsOTC = {u'63329656':'orgType',
        u'63329668':'companyName',
        u'63350957':'existingCustomer',
        u'63350998':'lbcUsername',
        u'63329635-1':'firstName',
        u'63329635-2':'lastName',
        u'63329636':'email',
        u'63352087':'phoneNumber',
        u'63329703':'estVol',
        u'63330253_0':'terms',
        u'63351124_0':'privacy',}	


def getSubmissions(pageNr, form_id):
    try:
        api_key = apiKeys['123FormBuilder']['1']['key']
        api_url_base = 'https://www.123formbuilder.com/api/'
        url = api_url_base + '/forms/' + form_id + '/submissions.json'

        headers = {'apiKey':api_key, 'pageSize':100, 'pageNr':pageNr}
        response = requests.post(url, params = headers)

        if response.status_code == 200:
            subs = json.loads(response.content)
            subs = subs['submissions'] 
            return subs
        else:
            return None
    except Exception as e:
        print("Error while getting submissions from form "  + str(form_id))
        print(e)

def getFormSubmissions(form_id):
    try:

        subs = []
        pageNr = 0
        # keep going until all submissions are found
        while True:
            subsOld = subs

            # getting submissions from next page
            newSubs = getSubmissions(pageNr, form_id)
            
            # catch any errors while getting submissions
            if newSubs == False:
                print("ERROR while getting form submissions.")
                return

            # add on subs from next page
            subs = subs + newSubs
            pageNr += 1

            # if no new submissions are added to list or there's not exactly 100 submissions, can stop searching for more
            if subsOld == subs or (len(subs)-len(subsOld)) % 100 != 0:
                break
        return subs
    except Exception as e:
        print("Error while getting LBC submissions")
        print(e)        

def processOTCSubmission(sub):
    try:
        # if not in db, add to db
        if len(sqlSelectRows("tblFormSubsOTC", "xml_id = '" + sub['xml_id'] + "'")) == 0:
        
            # parse data from submission
            emptyDic = {}
            fileUrls = {}
            for f in sub['fields']:

                if f['fieldid'] in fieldsIdsOTC and f['fieldvalue'] != "":
                    fieldName = fieldsIdsOTC[f['fieldid']]
                    emptyDic[fieldName] = f['fieldvalue'].strip()
                    if fieldName == 'firstName' or fieldName == 'lastName' or fieldName == 'streetAddress' or fieldName == 'city':
                        emptyDic[fieldName] = string.capwords(emptyDic[fieldName])

            emptyDic['xml_id'] = sub['xml_id']
            emptyDic['cc'] = sub['cc']
            emptyDic['date'] = sub['date']
            emptyDic['ip'] = sub['ip']
            emptyDic['date'] = sub['datestart']
            emptyDic['ref_id'] = sub['refid']

            if 'lbcUsername' in emptyDic:
                # try to find lbc username 
                customer = sqlSelectRows('tblLBCCustomers', 'username = "' + str(emptyDic['lbcUsername']) + '" COLLATE NOCASE')
                if customer:
                    # link otc enquiry to lbc customer
                    emptyDic['lbcUserFound'] = 1
                    sqlUpdateRows('tblLBCCustomers', 'username = "' + str(emptyDic['lbcUsername']) + '"', {'otc_enquiry':sub['refid']})
                else:
                    emptyDic['lbcUserFound'] = 0
            else:
                emptyDic['lbcUsername'] = ''
                emptyDic['lbcUserFound'] = 0
                

            for key in emptyDic:
                if isinstance(emptyDic[key], str):
                    emptyDic[key] = asciifyString(emptyDic[key]).replace("'","").replace('"','')


            # add the new submission to db
            sqlAddRow("tblFormSubsOTC", emptyDic)
            now = str(datetime.datetime.now())
            sqlAddRow("tblReminders", {'type':'OTC Enquiry', 'reference':sub['refid'], 'created_at':now, 'timestamp':now})
            reminderId = sqlSelectRows("tblReminders", "reference = '" + sub['refid'] + "'")[0]['id']

            # send confirmation message to telegram
            message = "NEW OTC ENQUIRY:" 
            message += "\nDate submitted: " + str(emptyDic['date'])
            if emptyDic['existingCustomer'] == 'Yes':
                message += "\nExisting Customer."
                if emptyDic['lbcUserFound']:
                    message += " LBC Username: " + str(emptyDic['lbcUsername'])
                else:
                    message += " LBC Username: " + str(emptyDic['lbcUsername']) + " (not found in database)"
                    message += "\nContact Details: "
            elif emptyDic['existingCustomer'] == 'No':
                message += "\nNew Customer. Contact Details:"
            message += "\nName: " + emptyDic['firstName'] + " " + emptyDic['lastName']
            message += "\nEmail: " + emptyDic['email']
            message += "\nPhone: " + emptyDic['phoneNumber']
            message += "\nEmail confirmation of receipt been sent. Need to contact them with details. /ignore" + str(reminderId) + " OR /ignore24Hours" + str(reminderId)
            print(message)
            telegramSendMessage(message, "reminders")

            # add email address to mailchimp
            try:
                d = addMailChimpSub(emptyDic['email'], emptyDic['firstName'], emptyDic['lastName'])
            except NameError:
                # email address has already been added to mailchimp
                print('Email has already been added to MailChimp: ' + str(emptyDic['email']))
            
            # send confirmation email to email address
            try:
                d = sendMailChimpEmail('f3616e5e0a', 'a82554d8fe', emptyDic['email'])
            except NameError:
                # email has already been sent to email address
                print('Email has already been sent to: ' + str(emptyDic['email']))

    except Exception as e:
        errorMessage = 'ERROR sorting OTC submission ' + sub['refid']
        errorMessage += '\n' + str(e)
        print(errorMessage)
        telegramSendMessage(errorMessage, 'errors')
        



def processLBCSubmission(sub):
            try:
            # if not in db, add to db
                if not sqlSelectRows("tblFormSubs", "xml_id = '" + sub['xml_id'] + "'"):
                
                    # parse data from submission
                    emptyDic = {}
                    fileUrls = {}
                    for f in sub['fields']:

                        if f['fieldid'] in fieldIds and f['fieldvalue'] != "":
                            fieldName = fieldIds[f['fieldid']]
                            if fieldName == 'bank_statement' or fieldName == 'selfie' or fieldName == 'note':
                                fileUrls[fieldName] = f['fieldvalue']
                            else:
                                emptyDic[fieldName] = f['fieldvalue'].strip()
                                if fieldName == 'firstName' or fieldName == 'lastName' or fieldName == 'streetAddress' or fieldName == 'city':
                                    emptyDic[fieldName] = string.capwords(emptyDic[fieldName])

                    emptyDic['xml_id'] = sub['xml_id']
                    emptyDic['cc'] = sub['cc']
                    emptyDic['date'] = sub['date']
                    emptyDic['ip'] = sub['ip']
                    emptyDic['date'] = sub['datestart']
                    emptyDic['ref_id'] = sub['refid']

                    if 'lbcRef' in emptyDic:
                        trade = sqlSelectRows("tblClosedTrades", "reference = '" + emptyDic['lbcRef'] + "'")
                        if len(trade) == 0:
                            trade = sqlSelectRows("tblClosedTrades", "transaction_id = '" + emptyDic['lbcRef'] + "'")
                    else:
                        trade = []
                    # find customer lbc username from trade db
                    if len(trade) > 0:
                        emptyDic['lbcUsername'] = str(trade[0]['customer_is'])
                        customer = sqlSelectRows("tblLBCCustomers", "username = '" + emptyDic['lbcUsername'] + "'")[0]
                        now = str(datetime.datetime.now())
                        sqlAddRow("tblReminders", {'type':'Docs Uploaded', 'reference':trade[0]['transaction_id'], 'created_at':now, 'timestamp':now})
                    else:
                        emptyDic['lbcUsername'] = ""

                    for key in emptyDic:
                        emptyDic[key] = asciifyString(emptyDic[key]).replace("'","").replace('"','')

                    if trade:
                        sqlUpdateRows('tblLBCCustomers', 'username = "' + trade[0]['customer_is'] + '"', {'form_id':emptyDic['ref_id']})

                    # add the new submission to db
                    sqlAddRow("tblFormSubs", emptyDic)
                    subId = sqlSelectRows("tblFormSubs", "ref_id = '" + emptyDic['ref_id'] + "'")[0]['id']

                    # send confirmation message to telegram
                    message = "NEW DOCS ON DROPBOX:" 
                    message += "\nIMPORTANT. Make sure the following details match documents: "
                    message += "\nName: " + emptyDic['firstName'] + " " + emptyDic['lastName']
                    message += "\nDOB: " + emptyDic['dob']
                    if emptyDic['lbcUsername']:
                        message += "\nUsername: " + str(emptyDic['lbcUsername'])
                        message += "\nLBC name: " + str(customer['real_name'])
                        message += "\nTrade Amount: " + str(trade[0]['fiat_amount'])
                    else:
                        message += "\nRef: " + emptyDic['lbcRef']
                    message += "\n/sendBankDetails" + str(subId)
                    print(message)
                    telegramSendMessage(message, "docUpload")

                    #add email address to mailchimp
                    try:
                        d = addMailChimpSub(emptyDic['email'], emptyDic['firstName'], emptyDic['lastName'])
                    except NameError:
                        # email address has already been added to mailchimp
                        print('Email has already been added to MailChimp: ' + str(emptyDic['email']))
                    
                    # send confirmation email to email address
                    try:
                        d = sendMailChimpEmail('25214feb7a', '38605340f2', emptyDic['email'])
                    except NameError:
                        # email has already been sent to email address
                        print('Email has already been sent to: ' + str(emptyDic['email']))



                    #### now move docs to dropbox
                    #fileUrls = [emptyDic['bankStatement'], emptyDic['selfie'], emptyDic['note']]
                    folder_name = emptyDic['firstName'] + " " + emptyDic['lastName']
                    file_name = emptyDic['firstName'] + "_" + emptyDic['lastName'] 
                    docNum = 1
                    print("Moving files for " + folder_name + " to dropbox")
                    try:
                        # find out if there is already a folder with that name
                        files = dbx.files_list_folder('/' + destination_folder + '/' + folder_name)
                        docNum = len(files.entries) + 1
                    except AttributeError:
                        docNum = 1
                    # download all the files attached in the form sub
                    for fileType in fileUrls:
                        f = requests.get(fileUrls[fileType], allow_redirects=True)

                        # find file name (with file ext in it)
                        session = requests.Session()
                        response = session.head(fileUrls[fileType])
                        contentType = response.headers['content-disposition']

                        # find ext type of file
                        ext = ''
                        for extType in lstExt:
                            if extType in contentType.lower():
                                ext = extType

                        if not ext:
                            telegramSendMessage('No extension type found for form sub ' + emptyDic['lbcUsername'] + '. Find out wtf is going on', 'error')
                            continue

                        # saving file to comp
                        file =  "C:/customer_docs/"  + file_name + "_" + fileType + "_" + str(docNum) + '.' + ext.lower()
                        open(file, 'wb').write(f.content)

                        # uploading file to dropbox
                        with open(file, 'rb') as f:
                            print("Uploading " + file + " to " + folder_name)
                            upload_location = '/' + destination_folder + '/' + folder_name + '/' + file_name + "_" + fileType + "_" + str(docNum) + '.' + ext.lower()
                            dbx.files_upload(f.read(), upload_location, mode=WriteMode('overwrite'))

                        # then delete from comp (don't know if can upload straight from python or need to save to hard disk first as above?)
                        os.remove(file)

                        docNum += 1
                         
            except Exception as e:
                    errorMessage = 'ERROR sorting LBC submissions'
                    errorMessage += '\n' + str(e)
                    print(errorMessage)
                    telegramSendMessage(errorMessage, 'errors')



def renameDbxFolder():
    try:
        path = '/Apps/123FormBuilder/Form-5429385'
        folders = dbx.files_list_folder(path).entries
        
        for f in folders:
            if '20' in f.name:
                xml_id = f.name.split('_')[-1] 
                sqlQuery = "xml_id LIKE '%" + xml_id + "%'"
                formSub = sqlSelectRows("tblFormSubs", sqlQuery)
                if len(formSub) == 1:
                    print("Renaming folder " + str(f.name) + ". To " + formSub[0]['firstName'] + " " + formSub[0]['lastName'])
                    from_path = path + "/" + f.name
                    to_path = path + '/' + str(formSub[0]['firstName']) + " " + str(formSub[0]['lastName'])
                    dbx.files_move(from_path, to_path, autorename=True)
    except Exception as e:
        print("Error while renaming folders")
        print(e)


def main():
    while True:
        print(str(datetime.datetime.now())[:-7] + ": Been 20 seconds since last checked forms, checking again.")

        # process lbc submissions
        lbcSubmissions = getFormSubmissions('5429385')
        for sub in lbcSubmissions:
            processLBCSubmission(sub)

        # process otc submissions
        otcSubmissions = getFormSubmissions('5433722')
        for sub in otcSubmissions:
            processOTCSubmission(sub)

        # rename folder names on dbx for formbuilder integration
        renameDbxFolder()

        # rest for 20 secs
        time.sleep(20)

if __name__ == "__main__":
    main()

    #print addMailChimpSub('richard@coinstand.co.uk', 'R', 'S')

