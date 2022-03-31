# ====================================================================
# core
import datetime
from django.contrib import messages
from django.templatetags.static import static
from zipfile import ZipFile
from django.utils import timezone
from cfts import settings as cftsSettings

# cryptography
import os
import string
import random
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key

# decorators
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache

from pages.views.auth import superUserCheck, staffCheck

# responses
from django.shortcuts import redirect, render
from django.template.loader import render_to_string

from django.http import JsonResponse, FileResponse, HttpResponse

# model/database stuff
from pages.models import *
from django.db.models import Max, Count, Q, Sum
from django.db.models import Case, When

import logging

logger = logging.getLogger('django')

# ====================================================================
# I really don't want to comment this file, there is so much hacky shit going on here

# function to collect Request objects and serve the transfer queue page, only available to staff users
@login_required
@user_passes_test(staffCheck, login_url='frontend', redirect_field_name=None)
@ensure_csrf_cookie
@never_cache
def queue(request):
    # instansiate the list that will contain all of the dictionaries of Request objects per network
    xfer_queues = []

    # used to determine which network tab on the queue shuold be selected by default
    activeTab = True

    # if else statement used to activate the easter egg on the queue page when the queue is completely empty
    # /queue/cookie will take the user to a cookie card matching game
    if str(request.path) == '/queue/cookie':
        # list of "cards" for the matching game
        cookieList1 = [
            {'name': "Chocolate Chip", 'path': static('img/cookies/cookie.png')},
            {'name': "Dark Chocolate Chip", 'path': static('img/cookies/darkChoc.png')},
            {'name': "Fortune", 'path': static('img/cookies/fortune.png')},
            {'name': "Iced Sugar", 'path': static('img/cookies/icedSugar.png')},
            {'name': "White Chocolate Macadamia Nut", 'path': static('img/cookies/macadamia.png')},
            {'name': "M&M", 'path': static('img/cookies/MnM.png')},
            {'name': "Oreo", 'path': static('img/cookies/oreo.png')},
            {'name': "Red Velvet", 'path': static('img/cookies/redVelvet.png')},
            {'name': "Sugar", 'path': static('img/cookies/sugar.png')},
            {'name': "Thin Mint", 'path': static('img/cookies/thinMint.png')},
        ]

        # second list of "cards"
        cookieList2 = random.sample(cookieList1, len(cookieList1))

        # combine and shuffle the cards
        random.shuffle(cookieList1)
        empty = cookieList1+cookieList2

    # sent a message to the empty queue page, kinda like a fortune cookie
    else:
        empty = random.choice([
            'These pipes are clean.',
            'LZ is clear.',
            'Nothing here. Why not work on metadata?',
            'Queue is empty -- just like my wallet.',
            "There's nothing here? Huh. That's gotta be an error ... ",
            "Xander was here.",
            "Is PKI working yet?",
            "It's probably the weekend right?",
            "Shoot a dart at Ron, tell him Xander told you to.",
            "I'll code tetris into this page one day.",
            "Don't let Jason ban everyone, 'cause he'll do it.",
            "Now anyone can be banned, so much power!",
            "A bug? In my code? Impossible.",
            "Deleting database... Just kidding",
            "Slow day?",
            "Pretty cards.",
            "Ban anyone today?",
            "Card games are fun too."
        ])

    # get all requests that are not part of a completed pull, do all filtering based on this cached query set
    ds_requests = Request.objects.filter(is_submitted=True, pull__date_complete__isnull=True).prefetch_related('files', 'target_email').select_related('user').annotate(
        files_in_request=Count('files__file_id'),
        needs_review=Count('files', filter=Q(files__user_oneeye=None) | Q(files__user_twoeye=None) & ~Q(files__user_oneeye=request.user)) -
        Count('files', filter=~Q(files__rejection_reason=None) & ~Q(files__user_oneeye=request.user) & ~Q(files__user_twoeye=request.user)),
        user_reviewing=Count('files', filter=Q(files__user_oneeye=request.user) & Q(files__date_oneeye=None) & Q(files__rejection_reason=None)) +
        Count('files', filter=Q(files__user_twoeye=request.user) & Q(files__date_twoeye=None) & Q(files__rejection_reason=None))).order_by('date_created')

    pending_nets = ds_requests.values_list('network', flat=True)
    ds_networks = Network.objects.filter(network_id__in=pending_nets)

    # for every network
    for net in ds_networks:
        # get information about the last pull that was done on this network
        last_pull = Pull.objects.values(
            'pull_number',
            'date_pulled',
            'user_pulled__username'
        ).filter(network__name=net.name).order_by('-date_pulled')[:1]

        queue = {
            'name': net.name,
            'order_by': net.sort_order,

            # add up all the counts, this is used to know if we need to display a network or not
            'count': 0,
            'file_count': 0,
            'activeNet': activeTab,
            'pending': 0,
            'centcom': 0,
            'other': 0,
            'pullable': 0,
            'hidden_dupes_pullable': 0,
            'hidden_dupes_pulled': 0,
            'pulled': 0,

            # the actuall set of Request objects
            'q': [],
            'o': [],
            'a': [],
            'p': [],
            'last_pull': last_pull,
        }

        activeTab = False

        # ... and add it to the list
        xfer_queues.append(queue)

    for rqst in ds_requests:
        for queue in xfer_queues:
            if queue['name'] == rqst.network.name:
                match_queue = queue
                break

        match_queue['count'] += 1

        if rqst.pull != None:
            match_queue['pulled'] += 1

            if rqst.rejected_dupe == True:
                match_queue['hidden_dupes_pulled'] += 1
            elif rqst.rejected_dupe == False:
                match_queue['p'].append(rqst)

        else:
            match_queue['file_count'] += rqst.files_in_request
            match_queue['pending'] += 1

            if rqst.ready_to_pull == True:
                match_queue['pullable'] += 1

                if rqst.rejected_dupe == True:
                    match_queue['hidden_dupes_pullable'] += 1
                elif rqst.rejected_dupe == False:
                    match_queue['a'].append(rqst)

            elif rqst.is_centcom == True:
                match_queue['centcom'] += 1
                match_queue['q'].append(rqst)

            elif rqst.is_centcom == False:
                match_queue['other'] += 1
                match_queue['o'].append(rqst)

    # sort the list of network queues into network order
    xfer_queues = sorted(xfer_queues, key=lambda k: k['order_by'], reverse=False)

    # create the request context
    rc = {'queues': xfer_queues, 'empty': empty, 'easterEgg': not activeTab}

    # roll that beautiful bean footage
    # ^-- I've always wondered what he meant by that, never did ask him
    return render(request, 'pages/queue.html', {'rc': rc})

# function to serve the request details page for a single Request object, only available to staff users
@login_required
@never_cache
@user_passes_test(staffCheck, login_url='frontend', redirect_field_name=None)
def transferRequest(request, id):
    # get the Request object
    rqst = Request.objects.get(request_id=id)
    # get the User object... for some reason, we already have the Request object, so why not just use that? You even used the Request object to get the User object......
    user = User.objects.get(user_id=rqst.user.user_id)

    # get all the Request objects with a matching request hash as the current Request object, not including the current Request object
    dupes = Request.objects.filter(pull__date_complete=None, request_hash=rqst.request_hash).exclude(request_id=rqst.request_id).order_by('-date_created')

    # check to see if the current Request object is the most recent object submitted with that request hash
    mostRecentDupe = False

    if dupes.count() > 0:
        if rqst.date_created > dupes[0].date_created:
            mostRecentDupe = True

    # get list of Rejections for the "Reject Files" button
    ds_rejections = Rejection.objects.filter(visible=True)
    rejections = []
    for row in ds_rejections:
        rejections.append({
            'rejection_id': row.rejection_id,
            'name': row.name,
            'subject': row.subject,
            'text': row.text
        })

    rc = {
        # 'User': str(user) + " ("+ str(user.auth_user.username) +")",
        'Date Submitted': rqst.date_created,
        'Source Email': user.source_email,
        'Destination Email': rqst.target_email.all()[0],
        'RHR Email': rqst.RHR_email,
        'Phone': user.phone,
        'Network': Network.objects.get(network_id=rqst.network.network_id),
        'org': rqst.org,
    }

    # wow thats a lot of context!
    return render(request, 'pages/transfer-request.html', {'rqst': rqst, 'rc': rc, 'dupes': dupes, 'mostRecentDupe': mostRecentDupe, 'rejections': rejections,
                                                           'centcom': rqst.is_centcom, 'notes': rqst.notes, "user_id": user.user_id, 'debug': cftsSettings.DEBUG})

# function to save staff added notes to a Request object, only avaliable to staff users
@login_required
@user_passes_test(staffCheck, login_url='frontend', redirect_field_name=None)
def requestNotes(request, requestid):
    # get notes, entered from request details page.
    # this will be a combination of any previously entered notes and the most recently entered in note
    postData = dict(request.POST.lists())
    notes = postData['notes'][0]

    # update the notes field on the Request object
    Request.objects.filter(request_id=requestid).update(notes=notes)
    rqst = Request.objects.get(request_id=requestid)
    messages.success(request, "Notes Saved")

    # call for a pull zip to be rewritten, Requests objects with notes will generate a _notes.txt in the pull zip
    try:
        pull_number = rqst.pull.pull_id
        createZip(request, rqst.network.name, pull_number)
    except AttributeError:
        print("Request not found in any pull.")

    return JsonResponse({'response': "Notes saved"})


# function to ban a user for a length of time, only available to superusers, staff uses can only request a user be banned
@login_required
@user_passes_test(staffCheck, login_url='queue', redirect_field_name=None)
def banUser(request, userid, requestid, ignore_strikes=False, perma_ban=False):
    # get the user to ban, grab the first from the returned filter results
    # I don't really remember why I chose to get the user this way, user_id is the database index for the object, which is always unique
    # ... I should have added comments while I was writing all this
    userToBan = User.objects.filter(user_id=userid)[0]

    # if they aren't banned then just use the strikes from the strikes field
    strikes = userToBan.strikes

    # used in the success message
    days = 0

    # if the function has a temp arg of "True" then give the user a 1 day ban, 1 day bans do not increase stike count but we do count them
    if ignore_strikes == "True":
        # if the user is already banned and we arrived back to this function that means the 'Escalate to Permanent Ban' button was clicked
        # set the user to 3 strikes, the following if statments will set them to perma ban
        if perma_ban == "True":
            User.objects.filter(user_id=userid).update(banned=True, strikes=4, banned_until=datetime.date.today().replace(year=datetime.date.today().year+1000))
        elif userToBan.banned == False and perma_ban == "False":
            User.objects.filter(user_id=userid).update(banned=True, temp_ban_count=F('temp_ban_count') + 1, banned_until=datetime.date.today() + datetime.timedelta(days=1))
            days = 1
        else:
            messages.error(request, "User may have already been banned, check user information below.")
            return redirect('/transfer-request/' + str(requestid))
    else:
        # users first ban, 3 days
        if strikes == 0:
            User.objects.filter(user_id=userid).update(banned=True, strikes=1, banned_until=datetime.date.today() + datetime.timedelta(days=3))
            days = 3
        # second ban, 7 days
        elif strikes == 1:
            User.objects.filter(user_id=userid).update(banned=True, strikes=2, banned_until=datetime.date.today() + datetime.timedelta(days=7))
            days = 7
        # third ban, 30 days
        elif strikes == 2:
            User.objects.filter(user_id=userid).update(banned=True, strikes=3, banned_until=datetime.date.today() + datetime.timedelta(days=30))
            days = 30
        # fourth ban, lifetime... assuming the user isn't alive 1000 years from now. I sure hope I'm not...
        elif strikes == 3:
            User.objects.filter(user_id=userid).update(banned=True, strikes=4, banned_until=datetime.date.today().replace(year=datetime.date.today().year+1000))
        # just incase any other stike number comes in
        else:
            pass

    if days == 0:
        messages.success(request, "User banned for a really long time")
    else:
        messages.success(request, "User banned for " + str(days) + " days")

    if cftsSettings.DEBUG == True:
        return redirect('/transfer-request/' + str(requestid))
    else:
        # generate a ban email template, but only when DEBUG == False... for my sanity
        eml = banEml(request, requestid, ignore_strikes, perma_ban)
        return redirect('/transfer-request/' + str(requestid) + "?eml=" + eml)

@login_required
@user_passes_test(staffCheck, login_url='queue', redirect_field_name=None)
def warnUser(request, userid, requestid):
    userToWarn = User.objects.filter(user_id=userid)
    userToWarn.update(account_warning_count=userToWarn[0].account_warning_count+1, last_warned_on=timezone.now())

    messages.success(request, "User warning issued")

    if cftsSettings.DEBUG == True:
        return redirect('/transfer-request/' + str(requestid))
    else:
        eml = warningEml(request, userToWarn[0].account_warning_count, userToWarn[0].source_email)
        return redirect('/transfer-request/' + str(requestid) + "?eml=" + eml)


# function to generate a ban email
@login_required
@user_passes_test(staffCheck, login_url='frontend', redirect_field_name=None)
def banEml(request, request_id, ignore_strikes, perma_ban):
    rqst = Request.objects.get(request_id=request_id)

    msgBody = "mailto:" + str(rqst.user.source_email) + "?subject=CFTS User Account Suspension&body="
    msgBody += render_to_string('partials/Queue_partials/banTemplate.html', {'rqst': rqst, 'ignore_strikes': ignore_strikes, 'perma_ban': perma_ban}, request)

    return msgBody

@login_required
@user_passes_test(staffCheck, login_url='queue', redirect_field_name=None)
def warnUser(request, userid, requestid, confirmWarn=False):
    userToWarn = User.objects.filter(user_id=userid)

    if userToWarn[0].last_warned_on != None and userToWarn[0].last_warned_on.date() == timezone.now().date() and confirmWarn == False:
        messages.warning(request, "User already warned today. Issue second warning? Click the warning button again to confirm.")

        return redirect('/transfer-request/' + str(requestid) + '?warning=true')
    else:
        userToWarn.update(account_warning_count=userToWarn[0].account_warning_count+1, last_warned_on=timezone.now())

        messages.success(request, "User warning issued")

        if cftsSettings.DEBUG == True:
            return redirect('/transfer-request/' + str(requestid))
        else:
            eml = warningEml(request, userToWarn[0].account_warning_count, userToWarn[0].source_email)
            return redirect('/transfer-request/' + str(requestid) + "?eml=" + eml)

# function to generate a warning email
@login_required
@user_passes_test(staffCheck, login_url='frontend', redirect_field_name=None)
def warningEml(request, warningCount, source_email):

    msgBody = "mailto:" + str(source_email) + "?subject=CFTS User Account Warning&body="
    msgBody += render_to_string('partials/Queue_partials/userWarningTemplate.html', {'warningCount': warningCount}, request)

    return msgBody


def encryptPhrase(byte_phrase, dest_network):
    keyPath = os.path.join(cftsSettings.KEYS_DIR, dest_network+"_PUB_KEY.pem")
    with open(keyPath, "rb") as dest_pub_pem:
        dest_pub_key = load_pem_public_key(dest_pub_pem.read())
        dest_pub_pem.close()

    return dest_pub_key.encrypt(byte_phrase, padding.OAEP(padding.MGF1(hashes.SHA256()), hashes.SHA256(), None))


def encryptFile(salt, nonce, byte_phrase, source_file):

    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390000)
    key = kdf.derive(byte_phrase)

    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce))
    encryptor = cipher.encryptor()

    with open(source_file, "rb") as inFile:
        cipherText = encryptor.update(inFile.read()) + encryptor.finalize()
        inFile.close()

    return cipherText


# function to create a zip file containing all pullable File objects for a given network
@login_required
@user_passes_test(staffCheck, login_url='frontend', redirect_field_name=None)
def createZip(request, network_name, rejectPull):

    # this variable is a bit misleading, rejectPull is used to determine wheter we are creating a completely new pull or modifying an already existing pull
    # in this case we are creating a new pull
    if rejectPull == 'false':
        # determine what number we should give the pull
        try:
            # get the last pull number for the current network
            maxPull = Pull.objects.filter(network=Network.objects.get(name=network_name)).latest('date_pulled')

            # reset the pull number everyday
            if(datetime.datetime.now().date() > maxPull.date_pulled.date()):
                pull_number = 1
            else:
                if maxPull.pull_number == None:
                    pull_number = 1
                else:
                    pull_number = maxPull.pull_number + 1

        except Pull.DoesNotExist:
            pull_number = 1

        # create the Pull object
        new_pull = Pull(
            pull_number=pull_number,
            network=Network.objects.get(name=network_name),
            # date_pulled=datetime.datetime.now(),
            date_pulled=timezone.now(),
            user_pulled=request.user,
        )

        # get all pullable requests for the current network
        qs = Request.objects.filter(
            network__name=network_name, pull=None, ready_to_pull=True, is_submitted=True)
        new_pull.save()

        pull = new_pull

    # we are modifying an already existing pull zip
    else:
        # get the pull and all its requests
        qs = Request.objects.filter(pull=rejectPull)
        pull = Pull.objects.filter(pull_id=rejectPull)[0]
        pull_number = pull.pull_number

    # construct the file path for the pull zip
    zipPath = os.path.join(cftsSettings.PULLS_DIR+"\\") + network_name + "_" + str(pull_number) + " " + str(pull.date_pulled.astimezone().strftime("%d%b %H%M")) + ".zip"

    zip = ZipFile(zipPath, "w")

    # zip folder structure looks like this, pull/user/request_#/files
    # list to keep track of which folder paths have been created so we don't overlap
    requestDirs = []
    # create a zip folder for every Request object
    for rqst in qs:
        zip_folder = str(rqst.user) + "/request_1"
        # get all non-rejected files in the current request
        theseFiles = rqst.files.filter(rejection_reason=None)
        # if the is_pii field is True on any of the File objects then encryptRequests will become true

        # only create a folder for a request if it has non-rejected files, we don't want empty folders because every file got rejected
        if theseFiles.exists():
            # if a user had multiple Request objects in a pull they will all need their own folder, this loop will create the unique request folder for the user
            i = 2
            while zip_folder in requestDirs:
                zip_folder = str(rqst.user) + "/request_" + str(i)
                i += 1

            requestDirs.append(zip_folder)

            crypt_info = {'encrypted': False, }

            if rqst.has_encrypted == True:
                phrase = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(32))
                byte_phrase = str.encode(phrase, 'utf-8')
                crypt_info = {'encrypted': True,
                              'salt': os.urandom(16),
                              'nonce': os.urandom(16),
                              'encryptedPhrase': encryptPhrase(byte_phrase, rqst.network.name)}

            # write all of the File objects to the folder we just created
            for f in theseFiles:
                if rqst.has_encrypted == True:
                    cipherText = encryptFile(crypt_info['salt'], crypt_info['nonce'], byte_phrase, f.file_object.path)
                    encrypt_file_path = zip_folder + "/" + str(f)
                    with zip.open(encrypt_file_path, 'w') as outFile:
                        outFile.write(cipherText)
                        outFile.close()
                else:
                    zip_path = os.path.join(zip_folder, str(f))
                    zip.write(f.file_object.path, zip_path)

            rqst_info_file_path = zip_folder + "/_request_info.txt"

            # originally a user could submit a request with multiple destination email addresses, that is no longer the case but the target_email field remains a many-to-many field
            # this loop was used to add all of the email addresses to a single file, but now it only ever loops through 1 Email object
            with zip.open(rqst_info_file_path, 'w') as fp:
                rqst_info = crypt_info

                rqst_info['email'] = rqst.target_email.all()[0].address
                rqst_info['user_id'] = rqst.user.user_identifier

                fp.write(str(rqst_info).encode('utf-8'))
                fp.close()

            #######################################################################################################################################
            if rqst.notes != "" and rqst.notes != None:
                notes_file_name = zip_folder + "/_notes.txt"

                with zip.open(notes_file_name, 'w') as nfp:
                    notes = rqst.notes
                    nfp.write(notes.encode('utf-8'))
                    nfp.close()

        else:
            print("all files in request rejected")
        # update the record
        if rejectPull == "false":
            rqst.pull_id = new_pull.pull_id
            rqst.date_pulled = new_pull.date_pulled
            rqst.save()
            files = rqst.files.all()
            files.update(pull=new_pull)

    zip.close()

    # see if we can't provide something more useful to the analysts - maybe the new pull number?
    if rejectPull == "false":
        messages.success(request, "Pull " + str(new_pull) + " successfully created")
        return JsonResponse({'pullNumber': new_pull.pull_number, 'datePulled': new_pull.date_pulled.strftime("%d%b %H%M").upper(), 'userPulled': str(new_pull.user_pulled)})
    else:
        return JsonResponse({'pullNumber': pull.pull_number, 'datePulled': pull.date_pulled.strftime("%d%b %H%M").upper(), 'userPulled': str(pull.user_pulled)})

@login_required
@user_passes_test(staffCheck, login_url='frontend', redirect_field_name=None)
def getFile(request, folder, fileID, fileName):
    response = FileResponse(
        open(os.path.join(folder, fileID, fileName), 'rb'))
    return response


@login_required
@user_passes_test(staffCheck, login_url='frontend', redirect_field_name=None)
def updateFileReview(request, fileID, rqstID, completeReview="False", quit="None", skipComplete=False):
    rqst = Request.objects.get(request_id=rqstID)
    file = File.objects.get(file_id=fileID)
    open_file = False
    save = True

    if file.user_oneeye == None and quit != "True":
        file.user_oneeye = request.user
        open_file = True
    elif file.user_oneeye == request.user and file.date_oneeye == None:
        if quit == "True":
            if file.user_twoeye != None:
                file.user_oneeye = file.user_twoeye
                file.date_oneeye = file.date_twoeye
                file.user_twoeye = None
                file.date_twoeye = None
            else:
                file.user_oneeye = None
                file.date_oneeye = None
        elif skipComplete == False and completeReview == "True":
            file.date_oneeye = timezone.now()
    elif file.user_twoeye == None and file.user_oneeye != request.user and quit != "True":
        file.user_twoeye = request.user
        open_file = True
    elif file.user_twoeye == request.user and file.date_twoeye == None:
        if quit == "True":
            file.user_twoeye = None
        elif skipComplete == False and completeReview == "True":
            file.date_twoeye = timezone.now()
    else:
        save = False

    if save == True:
        file.save()

    ready_to_pull = checkPullable(rqst)

    if save == False and ready_to_pull == True and rqst.pull != None:
        rqst.pull = None
        rqst.save()

    if open_file == True and cftsSettings.DEBUG == False:
        return redirect('/transfer-request/' + str(rqstID) + '?file=' + str(fileID))
    elif ready_to_pull == True:
        messages.success(request, "All files in request have been fully reviewed. Request ready to pull")
        if skipComplete == True:
            return ready_to_pull
        else:
            return redirect('/transfer-request/' + str(rqstID) + '?flash=false')
    else:
        return redirect('/transfer-request/' + str(rqstID))


def checkPullable(rqst):
    ready_to_pull = True
    for file in rqst.files.all():
        if file.date_twoeye == None:
            if file.rejection_reason == None:
                ready_to_pull = False
                break
        elif file.date_oneeye == None:
            if file.rejection_reason == None:
                ready_to_pull = False
                break

    if rqst.ready_to_pull != ready_to_pull:
        rqst.ready_to_pull = ready_to_pull
        rqst.save()

    return ready_to_pull


@login_required
@user_passes_test(superUserCheck, login_url='frontend', redirect_field_name=None)
def removeFileReviewer(request, stage):
    post = dict(request.POST.lists())
    rqst = Request.objects.get(request_id=post['rqst_id'][0])

    id_list = post['id_list[]']

    files = File.objects.filter(file_id__in=id_list)

    try:
        if stage == 1:
            for file in files:
                if file.user_twoeye != None:
                    file.user_oneeye = file.user_twoeye
                    file.date_oneeye = file.date_twoeye
                    file.user_twoeye = None
                    file.date_twoeye = None
                else:
                    file.user_oneeye = None
                    file.date_oneeye = None
                file.save()
            messages.success(request, 'Selected files have had their one eye reviewer removed')
        elif stage == 2:
            files.update(user_twoeye=None, date_twoeye=None)
            messages.success(request, 'Selected files have had their two eye reviewer removed')
    except:
        messages.error(request, 'Good job, you broke it. Something went wrong')

    if checkPullable(rqst) == False and rqst.pull != None:
        rqst.pull = None
        rqst.save()

    return HttpResponse({'response': 'Selected files have had their ' + str(stage) + ' eye review removed'})
