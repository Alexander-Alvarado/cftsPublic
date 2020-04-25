# core
import random
import datetime
from io import BytesIO, StringIO
from zipfile import ZipFile
from django.conf import settings

# decorators
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie

# responses
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, FileResponse

# model/database stuff
from .models import *
from django.db.models import Max, Count, Q, Sum

# unused for now
# from django.core.files.base import ContentFile



# Views here output/render a template.
def index( request ):
  return render(request, 'pages/index.html')

def consent( request ):
  return render(request, 'pages/consent.html')

def howTo( request ):
  return render(request, 'pages/howTo.html')

def resources( request ):
  return render(request, 'pages/resources.html')

def urlShortner( request ):
  return render(request, 'pages/urlShortner.html')

@login_required
@ensure_csrf_cookie
def analysts( request ):
  xfer_queues = []
  ds_networks = Network.objects.all()
  empty = random.choice( [ 
    'These pipes are clean.', 
    'LZ is clear.', 
    'Nothing here. Why not work on metadata?', 
    'Queue is empty -- just like my wallet.', 
    "There's nothing here? Huh. That's gotta be an error ... " 
  ] )

  for net in ds_networks:
    # get information about the last pull that was done on each network
    last_pull = Pull.objects.values( 
      'pull_number', 
      'date_pulled', 
      'user_pulled__username' 
    ).filter( network__name=net.name ).order_by( '-date_pulled' )[:1]

    # get all the xfer requests (pending and pulled) submitted for this network
    ds_requests = Request.objects.filter( 
      network__name=net.name, 
      is_submitted=True, 
      pull__date_complete__isnull=True 
      #, files__in=File.objects.filter( rejection_reason__isnull=True )
    ).order_by( '-date_created' )


    # count how many total files are in all the pending requests (excluding ones that have already been pulled)
    file_count = ds_requests.annotate( 
      files_in_request = Count( 'files__file_id', filter=Q( pull__date_pulled__isnull=True ) ) 
    ).aggregate( 
      files_in_dataset = Sum( 'files_in_request' ) 
    )

    # smoosh all the info together into one big, beautiful data object ...
    queue = { 
      'name': net.name, 
      'order_by': net.sort_order, 
      'file_count': file_count, 
      'count': ds_requests.count(), 
      'pending': ds_requests.aggregate( count = Count( 'request_id', filter=Q( pull__date_pulled__isnull=True ) ) ), 
      'q': ds_requests, 
      'last_pull': last_pull 
    }
    # ... and add it to the list
    xfer_queues.append( queue )
  
  # sort the list of network queues into network order
  xfer_queues = sorted( xfer_queues, key=lambda k: k['order_by'], reverse=False )
  
  # get list of Rejections for the "Reject Files" button
  ds_rejections = Rejection.objects.all()
  rejections = []
  for row in ds_rejections:
    rejections.append({
      'rejection_id': row.rejection_id,
      'name': row.name,
      'subject': row.subject,
      'text': row.text
    })

  # create the request context
  rc = { 'queues': xfer_queues, 'empty': empty, 'rejections': rejections }
  
  # roll that beautiful bean footage
  return render( request, 'pages/analysts.html', { 'rc': rc } )

@login_required
def transferRequest( request, id ):
  rqst = Request.objects.get( request_id = id )
  rc = { 
    'request_id': rqst.request_id,
    'date_created': rqst.date_created,
    'user': User.objects.get( user_id = rqst.user.user_id ),
    'network': Network.objects.get( network_id = rqst.network.network_id ),
    'files': rqst.files.all(),
    'target_email': Email.objects.get( email_id = rqst.target_email.email_id ),
    'is_submitted': rqst.is_submitted,
  }
  return render( request, 'pages/transfer-request.html', { 'rc': rc } )

@login_required
def createZip( request, network_name ):
  # create pull
  maxPull = Pull.objects.aggregate( Max( 'pull_number' ) )
  pull_number = 1 if maxPull['pull_number__max'] == None else maxPull['pull_number__max'] + 1

  new_pull = Pull( 
    pull_number = pull_number, 
    network = Network.objects.get( name = network_name ),
    date_pulled = datetime.datetime.now(),
    user_pulled = request.user,
  )
  new_pull.save()
  
  # create/overwrite zip file
  zipPath =  os.path.join( settings.STATICFILES_DIRS[0], "files\\" ) + network_name + "_" + str( pull_number ) + ".zip"
  zip = ZipFile( zipPath, "w" )

  #select Requests based on network and status
  qs = Request.objects.filter( network__name = network_name, pull = None )

  # for each xfer request ...
  for rqst in qs:
    zip_folder = str( rqst.user )
    theseFiles = rqst.files.all()

    # add their files to the zip in the folder of their name
    for f in theseFiles:
      zip_path = os.path.join( zip_folder, str( f ) )
      zip.write( f.file_object.path, zip_path )

    # create and add the target email file
    email_file_name = str( rqst.target_email )
    fp = open( email_file_name, "w" )
    fp.close()
    zip.write( email_file_name, os.path.join( zip_folder, email_file_name ) )
    os.remove( email_file_name )

    # update the record
    rqst.pull_id = new_pull.pull_id
    rqst.save()

  zip.close()

  # see if we can't provide something more useful to the analysts - maybe the new pull number?
  return JsonResponse( { 'pullNumber': new_pull.pull_number, 'datePulled': new_pull.date_pulled.strftime( "%d%b %H%M" ).upper(), 'userPulled': str( new_pull.user_pulled ) } )

@login_required
def pulls( request ):
  # request context
  rc = {
    'bodyText': 'This is the Pulls dashboard',
    'pull_history': []
  }

  networks = Network.objects.all()

  # get last 10 pull data for each network
  for net in networks:
    # get information about the last pull that was done on each network
    pulls = Pull.objects.filter( network__name=net.name ).order_by( '-date_pulled' )[:5]
    these_pulls = []
    for pull in pulls:
      this_pull = {
        'pull_id': pull.pull_id,
        'pull_number': pull.pull_number,
        'pull_date': pull.date_pulled,
        'pull_user': pull.user_pulled,
        'date_oneeye': pull.date_oneeye,
        'date_twoeye': pull.date_twoeye,
        'date_complete': pull.date_complete,
        'pull_network': net.name
      }
      these_pulls.append( this_pull )
    rc['pull_history'].append( these_pulls )

  return render( request, 'pages/pulls.html', { 'rc': rc } )

@login_required
def pullsOneEye( request, id ):
  thisPull = Pull.objects.get( pull_id = id )
  thisPull.date_oneeye = datetime.datetime.now()
  thisPull.user_oneeye = request.user
  thisPull.save()
  return JsonResponse( { 'id': id } )

@login_required
def pullsTwoEye( request, id ):
  thisPull = Pull.objects.get( pull_id = id )
  thisPull.date_twoeye = datetime.datetime.now()
  thisPull.user_twoeye = request.user
  thisPull.save()
  return JsonResponse( { 'id': id } )

@login_required
def pullsDone( request, id, cd ):
  thisPull = Pull.objects.get( pull_id = id )
  thisPull.date_complete = datetime.datetime.now()
  thisPull.user_complete = request.user
  thisPull.disc_number = cd
  thisPull.save()
  return JsonResponse( { 'id': id } )

@login_required
def setReject( request ):
  thestuff = dict( request.POST.lists() )

  reject_id = thestuff[ 'reject_id' ]
  request_id = thestuff[ 'request_id' ]
  id_list = thestuff[ 'id_list[]' ]
  
  # update the files to set the rejection
  File.objects.filter( file_id__in = id_list ).update( rejection_reason_id = reject_id[0] )

  # recreate the zip file for the pull
  someRequest = Request.objects.get( request_id = request_id )
  network_name = someRequest.network__name
  pull_number = someRequest.pull__pull_number

  zipPath =  os.path.join( settings.STATICFILES_DIRS[0], "files\\" ) + network_name + "_" + str( pull_number ) + ".zip"
  zip = ZipFile( zipPath, "w" )

  #select Requests based on pull
  qs = Request.objects.filter( pull__pull_id = someRequest.pull__pull_id, file__rejection_reason = None )

  # for each xfer request ...
  for rqst in qs:
    zip_folder = str( rqst.user )
    theseFiles = rqst.files.all()

    # add their files to the zip in the folder of their name
    for f in theseFiles:
      zip_path = os.path.join( zip_folder, str( f ) )
      zip.write( f.file_object.path, zip_path )

    # create and add the target email file
    email_file_name = str( rqst.target_email )
    fp = open( email_file_name, "w" )
    fp.close()
    zip.write( email_file_name, os.path.join( zip_folder, email_file_name ) )
    os.remove( email_file_name )

  zip.close()

  return JsonResponse( { 'mystring': 'isgreat' } )

@login_required
def archive( request ):
  requests = Request.objects.filter( is_submitted = True )
  rc = { 'requests': requests }
  return render( request, 'pages/archive.html', { 'rc': rc } )

@login_required
def toolsMakeFiles( request ):
  unclass = Classification.objects.get( abbrev='U' )
  return HttpResponse( 'Made the files' )
  '''
  for i in range( 16, 20 ):
    # filename
    new_f = 'textfile_' + str(i) + '.txt'
    # new CFTS File object
    new_file = File( classification = unclass )
    # save the new CFTS file
    new_file.save()
    # save the Django File into the CFTS File
    new_file.file_object.save( new_f, ContentFile( new_f ) )
  '''

@login_required
def apiGetUser( request, id ):
  user = User.objects.get( user_id = id )
  data = {
    'user_id': user.user_id,
    'first_name': user.name_first,
    'last_name': user.name_last,
    'email': user.email.address
  }
  return JsonResponse( data )