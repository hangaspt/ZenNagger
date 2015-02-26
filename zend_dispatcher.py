#!/usr/bin/python
import json
import requests
import sys
import getopt
import logging


logging.basicConfig(filename='/tmp/zendesk_dispacher.log',format='%(asctime)s [%(levelname)s] - %(funcName)20s() - %(message)s',level=logging.DEBUG)


#Zendesk account info
api_url = 'https://<account>.zendesk.com/api/v2/'
user = 'user@host.com'
pwd = 'password'

def getIDFromExternalID(eid):

   logging.info('Searching for tickets with external_id of:'+str(eid))

   query_data = 'external_id:'+str(eid)
   url = api_url + 'search.json?query='+query_data
   response = requests.get(url, auth=(user, pwd))

   if response.status_code != 200: 
       #print('Status:', response.status_code, 'Problem with the request. Exiting.')
       logging.error('Error completing the external web request, http_error %s',response.status_code);	
       return -1
   logging.debug('Request completed');
  
   # Decode the JSON response into a dictionary and use the data
   data = response.json()
   result = data['results'] 
   count=data['count']	
   logging.debug('found %s records',count)
    
   if count == 0:
      logging.info('No previous ticket found with an external_id of %s, creating one.',eid)
      return 0  # No previous ticket
   elif count != 1:
      logging.info('Multiple tickets found with an external_id of %s. Ambigous result. Quitting',eid)
      return -1  #None or ambigous records
   else:
      logging.info('Found an existing ticked with id %s for an external_if of %s',result[0]['id'],eid)
      result = data['results'] 
      return result[0]['id']



def createTicket(external_id,host,service,state,statetype,output,longoutput):
	
   logging.debug('external_id: %s',external_id);
   logging.debug('service: %s',service);
   logging.debug('host: %s',host);
   logging.debug('state: %s',state);
   logging.debug('statetype: %s',statetype);
   logging.debug('output: %s',output);
   logging.debug('longoutput: %s',longoutput);

   if service ==  '':
      subject = '[HOST] %s has raised an alarm' % (host)
      body = 'Host: %s\nState: %s\nState Type: %s\nDetails:\n%s\n%s' % (host,state, statetype,output,longoutput)
   else:
      subject = '[SERVICE] %s on %s has raised an alarm' % (service, host)
      body = 'Service: %s\nHost: %s\nState: %s\nState Type: %s\nDetails:\n%s\n%s' % (service, host,state, statetype,output,longoutput)




   data = {'ticket': {'external_id': external_id,'subject': subject, 'comment': {'body': body}}}
   payload = json.dumps(data)

   url = api_url + 'tickets.json'
   headers = {'content-type': 'application/json'}
   response = requests.post(url, data=payload, auth=(user, pwd), headers=headers)
   logging.info('Request return with http_status %s',response.status_code);	
   data = response.json()

   if response.status_code == 201:
      data = response.json()
      newTicketId=data['ticket']['id']
      logging.debug('Ticket created with id %s',newTicketId)
      return newTicketId
   else:
      logging.info('Error creating the new ticket')
      return -1



def updateTicket(tid,service,host,state,statetype,output,longoutput,solved):
   logging.debug('ticket_id: %s',tid);
   logging.debug('service: %s',service);
   logging.debug('host: %s',service);
   logging.debug('state: %s',state);
   logging.debug('statetype: %s',statetype);
   logging.debug('output: %s',output);
   logging.debug('longoutput: %s',longoutput);

   if service ==  '':
      body = 'Host: %s\nState: %s\nState Type: %s\nDetails:\n%s\n%s' % (host,state, statetype,output,longoutput)
   else:
      body = 'Service: %s\nHost: %s\nState: %s\nState Type: %s\nDetails:\n%s\n%s' % (service, host,state, statetype,output,longoutput)


   if solved:
   	data = { 'ticket': { 'status':'solved','comment': { 'body': body } } }
   else:
   	data = { 'ticket': { 'comment': { 'body': body } } }
   payload = json.dumps(data)

   url = api_url + 'tickets/' + str(tid) + '.json'
   headers = {'content-type': 'application/json'}
   response = requests.put(url, data=payload, auth=(user, pwd), headers=headers)

   if response.status_code != 200: 
       rdata = response.content
       logging.error('Error completing the external web request, http_error %s',response.status_code)
       logging.error('Server said %s',rdata)
       sys.exit(1)
   else:
       return True



def main(argv):
   service = ''
   body = ''
   external_id = ''
   last_external_id = ''
   host = ''
   state = ''
   statetype = ''
   output = ''
   longoutput = ''

   logging.info('Event Handler call')

   try:
      opts, args = getopt.getopt(argv,"i:l:h:s:",["help","id=","lid=","hostname=","service=","","state=","statetype=","output=","longoutput="])
   except getopt.GetoptError:
      print sys.argv[0]+' -i <id> -l<lastid> -h<hostname> -s <subject> -b <body>'
      logging.error("Wrong parameters specified. Quiting.")
      sys.exit(2)

   for opt, arg in opts:
      if opt == '--help':
         print sys.argv[0]+' -i id -s <subject> -b <body>'
         sys.exit()
      elif opt in ("-i", "--id"):
         external_id = arg   
      elif opt in ("-l", "--lid"):
         last_external_id = arg   
      elif opt in ("-h", "--hostname"):
         host = arg   
      elif opt in ("-s", "--service"):
         service = arg
      elif opt in ("--state"):
         state = arg   
      elif opt in ("--statetype"):
         statetype = arg   
      elif opt in ("--output"):
         output = arg   
      elif opt in ("--longoutput"):
         longoutput = arg   

   logging.debug('external_id: [%s]',external_id)
   logging.debug('last_external_id: [%s]',last_external_id)
   logging.debug('host: [%s]',host)
   logging.debug('service: [%s]',service)
   logging.debug('state: [%s]',state)
   logging.debug('statetype: [%s]',statetype)
   logging.debug('output: [%s]',output)
   logging.debug('longoutput: [%s]',longoutput)




   if external_id == '0':
      # extenal id of 0 in nagios means the service is OK or in a RECOVERED condition. The last_external_id contatins the external_id of the recovered event.
      # solve issue matching the last_externa_id
      ticket_id = getIDFromExternalID(last_external_id)
      logging.debug("Updating existing ticket with solve")
      updateTicket(ticket_id,service,host,state,statetype,output,longoutput,True)
      logging.info("Ticket auto solved. Exiting");
   else:
      #it is a new problem or an update to an existing problem.
      ticket_id = getIDFromExternalID(external_id)
      logging.debug("Proceeding with ticket_id of %s",ticket_id)
   
      if  ticket_id == -1:
      	logging.debug("Invalid or ambiguous ticket numbers. Cannot continue. Quiting")
      	sys.exit(1)
      elif ticket_id == 0:
       	#this is a new issue
       	logging.debug("Create a new ticket. External_ID: %s",external_id)
       	ticketID = createTicket(external_id,host,service,state,statetype,output,longoutput)
      	logging.info("Created a new ticket with id: %s",ticketID)
      else:
        logging.debug("Updating existing ticket. Ticket_id: %s",ticket_id)
        updateTicket(ticket_id,service,host,state,statetype,output,longoutput,False)


   logging.info("Exiting");

if __name__ == "__main__":
    main(sys.argv[1:])
