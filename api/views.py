from django.shortcuts import render
from datetime import datetime
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from Applicants.models import Applicant, Barangay, ApplicantUpdateRequest, ApplicantTransferRequest, ApplicantReactivationRequest, ApplicantReinstatementRequest
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

@csrf_exempt
@require_POST
def verify_applicant_for_new_registration(request):

    # =========================================================
    # GET DATA FROM REACT
    # =========================================================

    lastname = request.POST.get(
        "lastname",
        ""
    ).strip()

    firstname = request.POST.get(
        "firstname",
        ""
    ).strip()

    middlename = request.POST.get(
        "middlename",
        ""
    ).strip()

    birthdate = request.POST.get(
        "birthdate",
        ""
    ).strip()

    # =========================================================
    # VALIDATE REQUIRED FIELDS
    # =========================================================

    if not lastname:
        return JsonResponse(
            {
                "success": False,
                "exists": False,
                "message": "Last name is required."
            },
            status=400
        )

    if not firstname:
        return JsonResponse(
            {
                "success": False,
                "exists": False,
                "message": "First name is required."
            },
            status=400
        )

    if not middlename:
        return JsonResponse(
            {
                "success": False,
                "exists": False,
                "message": "Middle name is required."
            },
            status=400
        )

    if not birthdate:
        return JsonResponse(
            {
                "success": False,
                "exists": False,
                "message": "Birthdate is required."
            },
            status=400
        )

    # =========================================================
    # VALIDATE BIRTHDATE
    # =========================================================

    try:

        birthdate = datetime.strptime(
            birthdate,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        return JsonResponse(
            {
                "success": False,
                "exists": False,
                "message": "Invalid birthdate."
            },
            status=400
        )

    # =========================================================
    # CHECK EXISTING APPLICANT
    # =========================================================

    exists = Applicant.objects.filter(
        lastname__iexact=lastname,
        firstname__iexact=firstname,
        middlename__iexact=middlename,
        birthdate=birthdate
    ).exists()

    # =========================================================
    # EXISTING APPLICANT
    # =========================================================

    if exists:

        return JsonResponse(
            {
                "success": True,
                "exists": True,
                "message": (
                    "An applicant with the same "
                    "name and birthdate already exists."
                )
            }
        )

    # =========================================================
    # NO EXISTING APPLICANT
    # =========================================================

    return JsonResponse(
        {
            "success": True,
            "exists": False,
            "message": (
                "No existing applicant was found. "
                "You may proceed with New Registration."
            )
        }
    )


def barangay_list(request):
    barangays = Barangay.objects.all().order_by("name")

    data = [
        {
            "id": barangay.id,
            "name": barangay.name,
        }
        for barangay in barangays
    ]

    return JsonResponse(data, safe=False)

@csrf_exempt
def new_registration_api(request):

    # =========================================================
    # ONLY POST ALLOWED
    # =========================================================

    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "error": "Only POST requests are allowed."
            },
            status=405
        )

    # =========================================================
    # READ JSON
    # =========================================================

    try:
        data = json.loads(request.body)

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON data."
            },
            status=400
        )

    # =========================================================
    # GET DATA
    # =========================================================

    lastname = str(
        data.get("lastname", "")
    ).strip()

    firstname = str(
        data.get("firstname", "")
    ).strip()

    middlename = str(
        data.get("middlename", "")
    ).strip()

    age = data.get("age")

    sex = str(
        data.get("sex", "")
    ).strip()

    birthdate = data.get("birthdate")

    birthplace = str(
        data.get("birthplace", "")
    ).strip()

    brgy_id = data.get("brgy")

    province = str(
        data.get("province", "Albay")
    ).strip()

    municipality = str(
        data.get("municipality", "Pio Duran")
    ).strip()

    phone = str(
        data.get("phone", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip().lower()

    pwd_status = data.get(
        "pwd_status",
        "NO"
    )

    citizenship_status = data.get(
        "citizenship_status",
        "BY_BIRTH"
    )

    father = str(
        data.get("father", "")
    ).strip()

    mother = str(
        data.get("mother", "")
    ).strip()

    # =========================================================
    # BASIC VALIDATION
    # =========================================================

    if not lastname:
        return JsonResponse(
            {
                "success": False,
                "error": "Last name is required."
            },
            status=400
        )

    if not firstname:
        return JsonResponse(
            {
                "success": False,
                "error": "First name is required."
            },
            status=400
        )

    if not middlename:
        return JsonResponse(
            {
                "success": False,
                "error": "Middle name is required."
            },
            status=400
        )

    if age in [None, ""]:
        return JsonResponse(
            {
                "success": False,
                "error": "Age is required."
            },
            status=400
        )

    if not sex:
        return JsonResponse(
            {
                "success": False,
                "error": "Sex is required."
            },
            status=400
        )

    if not birthdate:
        return JsonResponse(
            {
                "success": False,
                "error": "Birthdate is required."
            },
            status=400
        )

    if not birthplace:
        return JsonResponse(
            {
                "success": False,
                "error": "Birthplace is required."
            },
            status=400
        )

    if not brgy_id:
        return JsonResponse(
            {
                "success": False,
                "error": "Please select a barangay."
            },
            status=400
        )

    if not phone:
        return JsonResponse(
            {
                "success": False,
                "error": "Phone number is required."
            },
            status=400
        )

    if not email:
        return JsonResponse(
            {
                "success": False,
                "error": "Email address is required."
            },
            status=400
        )

    if not father:
        return JsonResponse(
            {
                "success": False,
                "error": "Father's name is required."
            },
            status=400
        )

    if not mother:
        return JsonResponse(
            {
                "success": False,
                "error": "Mother's name is required."
            },
            status=400
        )

    # =========================================================
    # AGE VALIDATION
    # =========================================================

    try:
        applicant_age = int(age)

    except (ValueError, TypeError):
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid age."
            },
            status=400
        )

    if applicant_age <= 0:
        return JsonResponse(
            {
                "success": False,
                "error": "Age must be greater than zero."
            },
            status=400
        )

    # =========================================================
    # PHONE VALIDATION
    # =========================================================

    if not phone.isdigit():
        return JsonResponse(
            {
                "success": False,
                "error": "Phone number must contain numbers only."
            },
            status=400
        )

    if len(phone) != 11:
        return JsonResponse(
            {
                "success": False,
                "error": "Phone number must contain 11 digits."
            },
            status=400
        )

    # =========================================================
    # EMAIL CHECK
    # =========================================================

    if Applicant.objects.filter(
        email__iexact=email
    ).exists():

        return JsonResponse(
            {
                "success": False,
                "error": "An applicant with this email address already exists."
            },
            status=400
        )

    # =========================================================
    # GET BARANGAY
    # =========================================================

    try:

        barangay = Barangay.objects.get(
            id=brgy_id
        )

    except Barangay.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Selected barangay does not exist."
            },
            status=400
        )

    # =========================================================
    # CREATE APPLICANT
    # =========================================================

    try:

        applicant = Applicant.objects.create(

            lastname=lastname,

            firstname=firstname,

            middlename=middlename,

            age=applicant_age,

            sex=sex,

            birthdate=birthdate,

            birthplace=birthplace,

            brgy=barangay,

            province=province,

            municipality=municipality,

            phone=phone,

            email=email,

            # =================================================
            # FORCE NEW REGISTRATION
            # =================================================

            application_type="NEW",

            # =================================================
            # DEFAULT VALUES
            # =================================================

            pwd_status=pwd_status,

            citizenship_status=citizenship_status,

            status="PENDING",

            verification_status="UNVERIFIED",

            father=father,

            mother=mother,

            is_active=True,

            is_senior=applicant_age >= 60,
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "error": "Unable to create registration."
            },
            status=500
        )

    # =========================================================
    # SUCCESS
    # =========================================================

    return JsonResponse(
        {
            "success": True,
            "message": "New registration submitted successfully.",
            "applicant_id": applicant.id,
            "application_type": applicant.application_type,
            "status": applicant.status,
            "verification_status": applicant.verification_status,
            "created_at": applicant.date_joined,
        },
        status=201
    )

@csrf_exempt
@require_POST
def create_applicant_update_request(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON data."
        }, status=400)

    applicant_id = data.get("applicant_id")

    if not applicant_id:
        return JsonResponse({
            "success": False,
            "error": "Applicant ID is required."
        }, status=400)

    # =========================================================
    # GET EXISTING APPLICANT
    # =========================================================
    applicant = (
        Applicant.objects
        .select_related("brgy")
        .filter(
            id=applicant_id,
            is_active=True
        )
        .first()
    )

    if not applicant:
        return JsonResponse({
            "success": False,
            "error": "Applicant not found or inactive."
        }, status=404)

    # =========================================================
    # GET FORM DATA
    # =========================================================
    lastname = str(data.get("lastname", "")).strip()
    firstname = str(data.get("firstname", "")).strip()
    middlename = str(data.get("middlename", "")).strip()

    age = data.get("age")
    sex = str(data.get("sex", "")).strip().upper()

    birthdate = str(data.get("birthdate", "")).strip()
    birthplace = str(data.get("birthplace", "")).strip()

    brgy_id = data.get("brgy")

    province = str(
        data.get("province", "Albay")
    ).strip()

    municipality = str(
        data.get("municipality", "Pio Duran")
    ).strip()

    phone = str(data.get("phone", "")).strip()
    email = str(data.get("email", "")).strip().lower()

    pwd_status = str(
        data.get("pwd_status", "NO")
    ).strip().upper()

    citizenship_status = str(
        data.get("citizenship_status", "BY_BIRTH")
    ).strip().upper()

    father = str(data.get("father", "")).strip()
    mother = str(data.get("mother", "")).strip()

    reason = str(
        data.get("reason", "")
    ).strip()

    # =========================================================
    # REQUIRED FIELDS
    # =========================================================
    required_fields = {
        "lastname": lastname,
        "firstname": firstname,
        "middlename": middlename,
        "age": age,
        "sex": sex,
        "birthdate": birthdate,
        "birthplace": birthplace,
        "brgy": brgy_id,
        "phone": phone,
        "email": email,
        "father": father,
        "mother": mother,
    }

    missing_fields = [
        field
        for field, value in required_fields.items()
        if value is None or str(value).strip() == ""
    ]

    if missing_fields:
        return JsonResponse({
            "success": False,
            "error": "Please complete all required fields.",
            "missing_fields": missing_fields
        }, status=400)

    # =========================================================
    # AGE VALIDATION
    # =========================================================
    try:
        age = int(age)
    except (TypeError, ValueError):
        return JsonResponse({
            "success": False,
            "error": "Invalid age."
        }, status=400)

    if age < 18:
        return JsonResponse({
            "success": False,
            "error": "Applicant must be at least 18 years old."
        }, status=400)

    # =========================================================
    # SEX VALIDATION
    # =========================================================
    valid_sex = {
        "MALE",
        "FEMALE"
    }

    if sex not in valid_sex:
        return JsonResponse({
            "success": False,
            "error": "Invalid sex."
        }, status=400)

    # =========================================================
    # BIRTHDATE VALIDATION
    # =========================================================
    try:
        parsed_birthdate = datetime.strptime(
            birthdate,
            "%Y-%m-%d"
        ).date()
    except (ValueError, TypeError):
        return JsonResponse({
            "success": False,
            "error": "Invalid birthdate format. Use YYYY-MM-DD."
        }, status=400)

    # =========================================================
    # BARANGAY VALIDATION
    #
    # IMPORTANT:
    # Barangay MODEL DOES NOT HAVE is_active.
    # Therefore DO NOT use:
    #
    # Barangay.objects.filter(
    #     id=brgy_id,
    #     is_active=True
    # )
    # =========================================================
    try:
        barangay = (
            Barangay.objects
            .filter(id=brgy_id)
            .first()
        )
    except (ValueError, TypeError):
        barangay = None

    if not barangay:
        return JsonResponse({
            "success": False,
            "error": "Selected barangay was not found."
        }, status=400)

    # =========================================================
    # PHONE VALIDATION
    # =========================================================
    if not phone.isdigit() or len(phone) != 11:
        return JsonResponse({
            "success": False,
            "error": "Phone number must contain exactly 11 digits."
        }, status=400)

    if not phone.startswith("09"):
        return JsonResponse({
            "success": False,
            "error": "Phone number must start with 09."
        }, status=400)

    # =========================================================
    # EMAIL VALIDATION
    # =========================================================
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({
            "success": False,
            "error": "Please provide a valid email address."
        }, status=400)

    # =========================================================
    # CHECK DUPLICATE EMAIL
    #
    # Allow the applicant to keep their existing email.
    # =========================================================
    duplicate_email = (
        Applicant.objects
        .filter(email__iexact=email)
        .exclude(id=applicant.id)
        .exists()
    )

    if duplicate_email:
        return JsonResponse({
            "success": False,
            "error": "This email address is already registered to another applicant."
        }, status=400)

    # =========================================================
    # PWD VALIDATION
    # =========================================================
    valid_pwd_status = {
        choice[0]
        for choice in Applicant.PWD_CHOICES
    }

    if pwd_status not in valid_pwd_status:
        return JsonResponse({
            "success": False,
            "error": "Invalid PWD status."
        }, status=400)

    # =========================================================
    # CITIZENSHIP VALIDATION
    # =========================================================
    valid_citizenship = {
        choice[0]
        for choice in Applicant.CITIZENSHIP_CHOICES
    }

    if citizenship_status not in valid_citizenship:
        return JsonResponse({
            "success": False,
            "error": "Invalid citizenship status."
        }, status=400)

    # =========================================================
    # CHECK EXISTING UPDATE REQUEST
    #
    # Prevent multiple active update requests.
    # =========================================================
    existing_request = (
        ApplicantUpdateRequest.objects
        .filter(
            applicant=applicant,
            status__in=["PENDING", "REVIEW"]
        )
        .first()
    )

    if existing_request:
        return JsonResponse({
            "success": False,
            "error": (
                "You already have an update request "
                "that is pending or currently under review."
            ),
            "request_id": existing_request.id,
            "status": existing_request.status
        }, status=400)

    # =========================================================
    # CREATE UPDATE REQUEST
    #
    # IMPORTANT:
    # This does NOT immediately modify Applicant.
    # The changes will only be applied after admin approval.
    # =========================================================
    update_request = ApplicantUpdateRequest.objects.create(
        applicant=applicant,

        lastname=lastname,
        firstname=firstname,
        middlename=middlename,

        age=age,
        sex=sex,

        birthdate=parsed_birthdate,
        birthplace=birthplace,

        brgy=barangay,

        province=province,
        municipality=municipality,

        phone=phone,
        email=email,

        pwd_status=pwd_status,
        citizenship_status=citizenship_status,

        father=father,
        mother=mother,

        reason=reason,

        status="PENDING"
    )

    # =========================================================
    # SUCCESS RESPONSE
    # =========================================================
    return JsonResponse({
        "success": True,
        "message": (
            "Your update request has been submitted successfully "
            "and is now pending review."
        ),
        "request_id": update_request.id,
        "status": update_request.status,
        "requested_at": update_request.requested_at.isoformat()
    }, status=201)

@csrf_exempt
@require_POST
def find_applicant(request):

    # =========================================================
    # READ JSON
    # =========================================================

    try:

        data = json.loads(request.body)

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON data."
            },
            status=400
        )


    # =========================================================
    # GET SEARCH DATA
    # =========================================================

    lastname = str(
        data.get("lastname", "")
    ).strip()

    firstname = str(
        data.get("firstname", "")
    ).strip()

    middlename = str(
        data.get("middlename", "")
    ).strip()

    birthdate = str(
        data.get("birthdate", "")
    ).strip()


    # =========================================================
    # REQUIRED VALIDATION
    # =========================================================

    if not lastname:

        return JsonResponse(
            {
                "success": False,
                "error": "Last name is required."
            },
            status=400
        )


    if not firstname:

        return JsonResponse(
            {
                "success": False,
                "error": "First name is required."
            },
            status=400
        )


    if not middlename:

        return JsonResponse(
            {
                "success": False,
                "error": "Middle name is required."
            },
            status=400
        )


    if not birthdate:

        return JsonResponse(
            {
                "success": False,
                "error": "Birthdate is required."
            },
            status=400
        )


    # =========================================================
    # BIRTHDATE
    # =========================================================

    try:

        parsed_birthdate = datetime.strptime(
            birthdate,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid birthdate."
            },
            status=400
        )


    # =========================================================
    # FIND APPROVED ACTIVE APPLICANT
    # =========================================================

    applicant = (
        Applicant.objects
        .select_related("brgy")
        .filter(

            lastname__iexact=lastname,

            firstname__iexact=firstname,

            middlename__iexact=middlename,

            birthdate=parsed_birthdate,

            is_active=True,

            status="APPROVED"

        )
        .first()
    )


    # =========================================================
    # NOT FOUND
    # =========================================================

    if not applicant:

        return JsonResponse(
            {
                "success": False,
                "exists": False,
                "error": (
                    "No approved registration was found "
                    "using the information provided."
                )
            },
            status=404
        )


    # =========================================================
    # RETURN APPLICANT
    # =========================================================

    return JsonResponse(
        {
            "success": True,

            "exists": True,

            "applicant": {

                "id": applicant.id,

                "lastname": applicant.lastname,

                "firstname": applicant.firstname,

                "middlename": applicant.middlename,

                "age": applicant.age,

                "sex": applicant.sex,

                "birthdate": (
                    applicant.birthdate.strftime(
                        "%Y-%m-%d"
                    )
                    if applicant.birthdate
                    else ""
                ),

                "birthplace": applicant.birthplace,

                "brgy": (
                    applicant.brgy.id
                    if applicant.brgy
                    else ""
                ),

                "brgy_id": (
                    applicant.brgy.id
                    if applicant.brgy
                    else ""
                ),

                "brgy_name": (
                    applicant.brgy.name
                    if applicant.brgy
                    else ""
                ),

                "province": applicant.province,

                "municipality": applicant.municipality,

                "phone": applicant.phone,

                "email": applicant.email,

                "pwd_status": applicant.pwd_status,

                "citizenship_status": (
                    applicant.citizenship_status
                ),

                "father": applicant.father,

                "mother": applicant.mother,

                "status": applicant.status,

                "verification_status": (
                    applicant.verification_status
                ),
            }
        },
        status=200
    )

@csrf_exempt
@require_POST
def create_applicant_transfer_request(request):

    # =========================================================
    # PARSE JSON
    # =========================================================

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON data."
        }, status=400)

    # =========================================================
    # GET FORM DATA
    # =========================================================

    lastname = str(
        data.get("lastname", "")
    ).strip()

    firstname = str(
        data.get("firstname", "")
    ).strip()

    middlename = str(
        data.get("middlename", "")
    ).strip()

    birthdate = str(
        data.get("birthdate", "")
    ).strip()

    current_brgy_id = data.get(
        "current_brgy"
    )

    new_brgy_id = data.get(
        "new_brgy"
    )

    current_municipality = str(
        data.get(
            "current_municipality",
            "Pio Duran"
        )
    ).strip()

    current_province = str(
        data.get(
            "current_province",
            "Albay"
        )
    ).strip()

    new_municipality = str(
        data.get(
            "new_municipality",
            "Pio Duran"
        )
    ).strip()

    new_province = str(
        data.get(
            "new_province",
            "Albay"
        )
    ).strip()

    reason = str(
        data.get(
            "reason",
            ""
        )
    ).strip()

    # =========================================================
    # REQUIRED FIELDS
    # =========================================================

    required_fields = {
        "lastname": lastname,
        "firstname": firstname,
        "middlename": middlename,
        "birthdate": birthdate,
        "current_brgy": current_brgy_id,
        "new_brgy": new_brgy_id,
    }

    missing_fields = [
        field
        for field, value in required_fields.items()
        if value is None or str(value).strip() == ""
    ]

    if missing_fields:
        return JsonResponse({
            "success": False,
            "error": "Please complete all required fields.",
            "missing_fields": missing_fields
        }, status=400)

    # =========================================================
    # BIRTHDATE VALIDATION
    # =========================================================

    try:
        parsed_birthdate = datetime.strptime(
            birthdate,
            "%Y-%m-%d"
        ).date()
    except (ValueError, TypeError):

        return JsonResponse({
            "success": False,
            "error": "Invalid birthdate format. Use YYYY-MM-DD."
        }, status=400)

    # =========================================================
    # FIND APPROVED APPLICANT
    #
    # Transfer should only be allowed for an existing
    # approved applicant.
    # =========================================================

    applicant = (
        Applicant.objects
        .select_related("brgy")
        .filter(
            lastname__iexact=lastname,
            firstname__iexact=firstname,
            middlename__iexact=middlename,
            birthdate=parsed_birthdate,
            status="APPROVED",
            is_active=True
        )
        .first()
    )

    if not applicant:

        return JsonResponse({
            "success": False,
            "exists": False,
            "error": (
                "No approved registration was found "
                "using the information provided."
            )
        }, status=404)

    # =========================================================
    # CURRENT BARANGAY
    # =========================================================

    try:
        current_barangay = (
            Barangay.objects
            .filter(id=current_brgy_id)
            .first()
        )
    except (ValueError, TypeError):

        current_barangay = None

    if not current_barangay:

        return JsonResponse({
            "success": False,
            "error": "Current barangay was not found."
        }, status=400)

    # =========================================================
    # VERIFY CURRENT BARANGAY
    #
    # The barangay entered by the applicant must match
    # the applicant's current registered barangay.
    # =========================================================

    if not applicant.brgy:

        return JsonResponse({
            "success": False,
            "error": (
                "Your existing registration does not have "
                "a registered barangay."
            )
        }, status=400)

    if applicant.brgy.id != current_barangay.id:

        return JsonResponse({
            "success": False,
            "error": (
                "The current barangay does not match "
                "your existing registration."
            )
        }, status=400)

    # =========================================================
    # NEW BARANGAY
    # =========================================================

    try:
        new_barangay = (
            Barangay.objects
            .filter(id=new_brgy_id)
            .first()
        )
    except (ValueError, TypeError):

        new_barangay = None

    if not new_barangay:

        return JsonResponse({
            "success": False,
            "error": "New barangay was not found."
        }, status=400)

    # =========================================================
    # PREVENT SAME BARANGAY
    # =========================================================

    if current_barangay.id == new_barangay.id:

        return JsonResponse({
            "success": False,
            "error": (
                "The new barangay must be different "
                "from your current barangay."
            )
        }, status=400)

    # =========================================================
    # PREVENT MULTIPLE ACTIVE TRANSFER REQUESTS
    # =========================================================

    existing_request = (
        ApplicantTransferRequest.objects
        .filter(
            applicant=applicant,
            status__in=[
                "PENDING",
                "REVIEW"
            ]
        )
        .first()
    )

    if existing_request:

        return JsonResponse({
            "success": False,
            "error": (
                "You already have a transfer request "
                "that is pending or currently under review."
            ),
            "request_id": existing_request.id,
            "status": existing_request.status
        }, status=400)

    # =========================================================
    # CREATE TRANSFER REQUEST
    #
    # Applicant is NOT changed here.
    # The actual transfer will happen only after
    # administrator approval.
    # =========================================================

    transfer_request = ApplicantTransferRequest.objects.create(

        applicant=applicant,

        current_brgy=current_barangay,
        new_brgy=new_barangay,

        current_municipality=current_municipality,
        current_province=current_province,

        new_municipality=new_municipality,
        new_province=new_province,

        reason=reason,

        status="PENDING"
    )

    # =========================================================
    # SUCCESS
    # =========================================================

    return JsonResponse({
        "success": True,
        "message": (
            "Your transfer request has been submitted "
            "successfully and is now pending review."
        ),
        "request_id": transfer_request.id,
        "status": transfer_request.status,
        "applicant_id": applicant.id,
        "current_barangay": current_barangay.name,
        "new_barangay": new_barangay.name,
        "requested_at": transfer_request.requested_at.isoformat()
    }, status=201)


@csrf_exempt
@require_POST
def create_applicant_reactivation_request(request):

    # =========================================================
    # PARSE JSON
    # =========================================================

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON data."
        }, status=400)

    # =========================================================
    # GET FORM DATA
    # =========================================================

    lastname = str(
        data.get("lastname", "")
    ).strip()

    firstname = str(
        data.get("firstname", "")
    ).strip()

    middlename = str(
        data.get("middlename", "")
    ).strip()

    birthdate = str(
        data.get("birthdate", "")
    ).strip()

    reason = str(
        data.get("reason", "")
    ).strip()

    # =========================================================
    # REQUIRED FIELDS
    # =========================================================

    required_fields = {
        "lastname": lastname,
        "firstname": firstname,
        "middlename": middlename,
        "birthdate": birthdate,
        "reason": reason,
    }

    missing_fields = [
        field
        for field, value in required_fields.items()
        if value is None or str(value).strip() == ""
    ]

    if missing_fields:
        return JsonResponse({
            "success": False,
            "error": "Please complete all required fields.",
            "missing_fields": missing_fields
        }, status=400)

    # =========================================================
    # BIRTHDATE VALIDATION
    # =========================================================

    try:
        parsed_birthdate = datetime.strptime(
            birthdate,
            "%Y-%m-%d"
        ).date()

    except (ValueError, TypeError):

        return JsonResponse({
            "success": False,
            "error": "Invalid birthdate format. Use YYYY-MM-DD."
        }, status=400)

    # =========================================================
    # FIND INACTIVE APPLICANT
    #
    # Reactivation is specifically for an applicant whose
    # existing registration is inactive.
    # =========================================================

    applicant = (
        Applicant.objects
        .select_related("brgy")
        .filter(
            lastname__iexact=lastname,
            firstname__iexact=firstname,
            middlename__iexact=middlename,
            birthdate=parsed_birthdate,
            is_active=False
        )
        .first()
    )

    if not applicant:

        # Check whether the applicant exists but is already active.
        active_applicant = (
            Applicant.objects
            .filter(
                lastname__iexact=lastname,
                firstname__iexact=firstname,
                middlename__iexact=middlename,
                birthdate=parsed_birthdate,
                is_active=True
            )
            .first()
        )

        if active_applicant:

            return JsonResponse({
                "success": False,
                "exists": True,
                "error": (
                    "This applicant is already active. "
                    "A reactivation request is not required."
                )
            }, status=400)

        return JsonResponse({
            "success": False,
            "exists": False,
            "error": (
                "No inactive registration was found "
                "using the information provided."
            )
        }, status=404)

    # =========================================================
    # CHECK EXISTING REACTIVATION REQUEST
    #
    # Prevent multiple PENDING or REVIEW requests.
    # =========================================================

    existing_request = (
        ApplicantReactivationRequest.objects
        .filter(
            applicant=applicant,
            status__in=[
                "PENDING",
                "REVIEW"
            ]
        )
        .first()
    )

    if existing_request:

        return JsonResponse({
            "success": False,
            "error": (
                "You already have a reactivation request "
                "that is pending or currently under review."
            ),
            "request_id": existing_request.id,
            "status": existing_request.status
        }, status=400)

    # =========================================================
    # CREATE REACTIVATION REQUEST
    #
    # IMPORTANT:
    # Do NOT set applicant.is_active=True here.
    #
    # The applicant will only be reactivated after the
    # administrator approves the request.
    # =========================================================

    reactivation_request = (
        ApplicantReactivationRequest.objects.create(
            applicant=applicant,
            reason=reason,
            status="PENDING"
        )
    )

    # =========================================================
    # SUCCESS RESPONSE
    # =========================================================

    return JsonResponse({
        "success": True,
        "message": (
            "Your reactivation request has been submitted "
            "successfully and is now pending review."
        ),
        "request_id": reactivation_request.id,
        "status": reactivation_request.status,
        "applicant_id": applicant.id,
        "applicant_name": str(applicant),
        "requested_at": (
            reactivation_request.requested_at.isoformat()
        )
    }, status=201)

@csrf_exempt
@require_POST
def create_applicant_reinstatement_request(request):

    try:
        data = json.loads(request.body)

    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON data."
        }, status=400)

    lastname = str(
        data.get("lastname", "")
    ).strip()

    firstname = str(
        data.get("firstname", "")
    ).strip()

    middlename = str(
        data.get("middlename", "")
    ).strip()

    birthdate = str(
        data.get("birthdate", "")
    ).strip()

    reason = str(
        data.get("reason", "")
    ).strip()

    required_fields = {
        "lastname": lastname,
        "firstname": firstname,
        "middlename": middlename,
        "birthdate": birthdate,
        "reason": reason,
    }

    missing_fields = [
        field
        for field, value in required_fields.items()
        if not value
    ]

    if missing_fields:
        return JsonResponse({
            "success": False,
            "error": "Please complete all required fields.",
            "missing_fields": missing_fields
        }, status=400)

    try:
        parsed_birthdate = datetime.strptime(
            birthdate,
            "%Y-%m-%d"
        ).date()

    except (ValueError, TypeError):
        return JsonResponse({
            "success": False,
            "error": (
                "Invalid birthdate format. "
                "Use YYYY-MM-DD."
            )
        }, status=400)

    # Find an existing inactive applicant.
    applicant = (
        Applicant.objects
        .select_related("brgy")
        .filter(
            lastname__iexact=lastname,
            firstname__iexact=firstname,
            middlename__iexact=middlename,
            birthdate=parsed_birthdate,
            is_active=False
        )
        .first()
    )

    if not applicant:

        # Check if the applicant exists but is already active.
        active_applicant = (
            Applicant.objects
            .filter(
                lastname__iexact=lastname,
                firstname__iexact=firstname,
                middlename__iexact=middlename,
                birthdate=parsed_birthdate,
                is_active=True
            )
            .first()
        )

        if active_applicant:
            return JsonResponse({
                "success": False,
                "exists": True,
                "error": (
                    "This applicant is already active. "
                    "A reinstatement request is not required."
                )
            }, status=400)

        return JsonResponse({
            "success": False,
            "exists": False,
            "error": (
                "No inactive registration was found "
                "using the information provided."
            )
        }, status=404)

    # Prevent multiple pending/review requests.
    existing_request = (
        ApplicantReinstatementRequest.objects
        .filter(
            applicant=applicant,
            status__in=[
                "PENDING",
                "REVIEW"
            ]
        )
        .first()
    )

    if existing_request:
        return JsonResponse({
            "success": False,
            "error": (
                "You already have a reinstatement request "
                "that is pending or currently under review."
            ),
            "request_id": existing_request.id,
            "status": existing_request.status
        }, status=400)

    # Create reinstatement request.
    reinstatement_request = (
        ApplicantReinstatementRequest.objects.create(
            applicant=applicant,
            reason=reason,
            status="PENDING"
        )
    )

    return JsonResponse({
        "success": True,
        "message": (
            "Your reinstatement request has been "
            "submitted successfully and is now "
            "pending review."
        ),
        "request_id": reinstatement_request.id,
        "status": reinstatement_request.status,
        "applicant_id": applicant.id,
        "applicant_name": str(applicant),
        "requested_at": (
            reinstatement_request.requested_at.isoformat()
        )
    }, status=201)