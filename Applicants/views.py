from django.shortcuts import render, redirect, get_object_or_404
from .models import Applicant, Barangay, ApplicantUpdateRequest, ApplicantTransferRequest, ApplicantReactivationRequest, ApplicantReinstatementRequest
import os
import re
from datetime import date
from django.utils.dateparse import parse_date

def home(request):

    return render(
        request,
        "applicant/home.html"
    )

def new_registration(request):
    barangays = Barangay.objects.all().order_by("name")

    template_name = "applicant/forms/new_registration.html"
    max_file_size = 5 * 1024 * 1024

    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}

    file_signatures = {
        ".pdf": lambda data: data.startswith(b"%PDF-"),
        ".jpg": lambda data: data.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
        ".png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    }

    civil_status_choices = {
        "Single",
        "Married",
        "Widowed",
        "Separated",
    }

    def render_error(message):
        return render(
            request,
            template_name,
            {
                "barangays": barangays,
                "error": message,
                "form_data": request.POST,
            },
        )

    if request.method == "POST":

        # =====================================================
        # PERSONAL INFORMATION
        # =====================================================

        lastname = request.POST.get("lastname", "").strip()
        firstname = request.POST.get("firstname", "").strip()
        middlename = request.POST.get("middlename", "").strip()

        age = request.POST.get("age", "").strip()
        sex = request.POST.get("sex", "").strip()
        birthdate_input = request.POST.get("birthdate", "").strip()
        birthplace = request.POST.get("birthplace", "").strip()

        # CIVIL STATUS: READ FROM THE FORM
        civil_status = request.POST.get(
            "civil_status", ""
        ).strip()

        # =====================================================
        # ADDRESS
        # Municipality and province are fixed server-side.
        # Do not trust values submitted by the browser.
        # =====================================================

        brgy_id = request.POST.get("brgy", "").strip()

        municipality = "Pio Duran"
        province = "Albay"

        # =====================================================
        # CONTACT INFORMATION
        # =====================================================

        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()

        # =====================================================
        # OTHER INFORMATION
        # =====================================================

        pwd_status = request.POST.get("pwd_status", "NO").strip()
        citizenship_status = request.POST.get(
            "citizenship_status", "BY_BIRTH"
        ).strip()

        father = request.POST.get("father", "").strip()
        mother = request.POST.get("mother", "").strip()

        # =====================================================
        # REQUIRED FIELD VALIDATION
        # =====================================================

        required_fields = [
            (lastname, "Last name is required."),
            (firstname, "First name is required."),
            (middlename, "Middle name is required."),
            (age, "Age is required."),
            (sex, "Sex is required."),
            (birthdate_input, "Birthdate is required."),
            (birthplace, "Birthplace is required."),
            (civil_status, "Please select your civil status."),
            (brgy_id, "Please select a barangay."),
            (phone, "Phone number is required."),
            (email, "Email address is required."),
            (father, "Father's name is required."),
            (mother, "Mother's name is required."),
        ]

        for value, message in required_fields:
            if not value:
                return render_error(message)

        # =====================================================
        # VALIDATE CIVIL STATUS
        # =====================================================

        if civil_status not in civil_status_choices:
            return render_error(
                "Please select a valid civil status."
            )

        # =====================================================
        # VALIDATE SEX
        # =====================================================

        if sex not in {"Male", "Female"}:
            return render_error("Please select a valid sex.")

        # =====================================================
        # VALIDATE AGE
        # =====================================================

        try:
            applicant_age = int(age)

            if applicant_age < 1 or applicant_age > 150:
                return render_error(
                    "Please enter an age between 1 and 150."
                )

        except (ValueError, TypeError):
            return render_error("Please enter a valid age.")

        # =====================================================
        # VALIDATE BIRTHDATE
        # =====================================================

        parsed_birthdate = parse_date(birthdate_input)

        if not parsed_birthdate:
            return render_error("Please enter a valid birthdate.")

        if parsed_birthdate > date.today():
            return render_error(
                "Birthdate cannot be in the future."
            )

        # =====================================================
        # VALIDATE PHONE NUMBER
        # =====================================================

        if not re.fullmatch(r"09[0-9]{9}", phone):
            return render_error(
                "Enter a valid 11-digit Philippine mobile number."
            )

        # =====================================================
        # VALIDATE EMAIL
        # =====================================================

        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError

        try:
            validate_email(email)
        except ValidationError:
            return render_error(
                "Please enter a valid email address."
            )

        if Applicant.objects.filter(email__iexact=email).exists():
            return render_error(
                "An applicant with this email address already exists."
            )

        # =====================================================
        # VALIDATE OTHER CHOICES
        # =====================================================

        valid_pwd_statuses = {
            value for value, label in Applicant.PWD_CHOICES
        }

        valid_citizenship_statuses = {
            value for value, label in Applicant.CITIZENSHIP_CHOICES
        }

        if pwd_status not in valid_pwd_statuses:
            return render_error("Please select a valid PWD status.")

        if citizenship_status not in valid_citizenship_statuses:
            return render_error("Please select a valid citizenship.")

        # =====================================================
        # GET BARANGAY
        # =====================================================

        try:
            barangay = Barangay.objects.get(id=brgy_id)

        except (Barangay.DoesNotExist, ValueError, TypeError):
            return render_error(
                "The selected barangay does not exist."
            )

        # =====================================================
        # VALIDATE UPLOADED DOCUMENT
        # =====================================================

        uploaded_document = request.FILES.get(
            "valid_id_document"
        )

        if not uploaded_document:
            return render_error(
                "Please upload your valid ID or supporting document."
            )

        if uploaded_document.size <= 0:
            return render_error(
                "The uploaded document is empty."
            )

        if uploaded_document.size > max_file_size:
            return render_error(
                "The uploaded document must not exceed 5 MB."
            )

        extension = os.path.splitext(
            uploaded_document.name
        )[1].lower()

        if extension not in allowed_extensions:
            return render_error(
                "Invalid document type. Upload a PDF, JPG, JPEG, or PNG file."
            )

        file_start = uploaded_document.read(16)
        uploaded_document.seek(0)

        signature_check = file_signatures.get(extension)

        if not signature_check or not signature_check(file_start):
            return render_error(
                "The uploaded file does not match its file type. "
                "Please upload a valid PDF, JPG, JPEG, or PNG document."
            )

        # =====================================================
        # CREATE APPLICANT
        # =====================================================

        applicant = Applicant(
            lastname=lastname,
            firstname=firstname,
            middlename=middlename,
            age=applicant_age,
            sex=sex,
            birthdate=parsed_birthdate,
            birthplace=birthplace,

            # SAVE CIVIL STATUS
            civil_status=civil_status,

            # ADDRESS
            brgy=barangay,
            province=province,
            municipality=municipality,

            # CONTACT
            phone=phone,
            email=email,

            # APPLICATION
            application_type="NEW",
            status="PENDING",
            verification_status="UNVERIFIED",

            # OTHER INFORMATION
            pwd_status=pwd_status,
            citizenship_status=citizenship_status,
            father=father,
            mother=mother,

            # UPLOADED DOCUMENT
            valid_id_document=uploaded_document,

            is_active=True,
            is_senior=applicant_age >= 60,
        )

        applicant.save()

        # =====================================================
        # REDIRECT TO SUCCESS PAGE
        # =====================================================

        return redirect(
            "registration-success",
            applicant_id=applicant.id,
        )

    # =========================================================
    # GET REQUEST
    # =========================================================

    return render(
        request,
        template_name,
        {
            "barangays": barangays,
        },
    )

def registration_success(request, applicant_id):

    applicant = get_object_or_404(
        Applicant,
        id=applicant_id
    )

    return render(
        request,
        "components/registration_success.html",
        {
            "applicant": applicant,
        }
    )


def verify_new_registration(request):

    if request.method == "POST":

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

        if not lastname:
            return render(
                request,
                "applicant/forms/verify_registration.html",
                {
                    "error": "Last name is required.",
                    "form_data": request.POST,
                }
            )

        if not firstname:
            return render(
                request,
                "applicant/forms/verify_registration.html",
                {
                    "error": "First name is required.",
                    "form_data": request.POST,
                }
            )

        if not middlename:
            return render(
                request,
                "applicant/forms/verify_registration.html",
                {
                    "error": "Middle name is required.",
                    "form_data": request.POST,
                }
            )

        if not birthdate:
            return render(
                request,
                "applicant/forms/verify_registration.html",
                {
                    "error": "Birthdate is required.",
                    "form_data": request.POST,
                }
            )

        applicant = Applicant.objects.filter(
            lastname__iexact=lastname,
            firstname__iexact=firstname,
            middlename__iexact=middlename,
            birthdate=birthdate,
        ).first()

        if applicant:

            return render(
                request,
                "applicant/forms/verify_registration.html",
                {
                    "applicant": applicant,
                    "form_data": request.POST,
                }
            )

        return redirect("new-registration")

    return render(
        request,
        "applicant/forms/verify_registration.html"
    )


def update_registration(request):
    template_name = "applicant/forms/update_registration.html"
    barangays = Barangay.objects.all().order_by("name")

    # =========================================================
    # HELPER: RENDER TEMPLATE WITH CONSISTENT CONTEXT
    # =========================================================

    def render_page(
        applicant=None,
        error=None,
        form_data=None,
        search_data=None,
    ):
        return render(
            request,
            template_name,
            {
                "applicant": applicant,
                "barangays": barangays,
                "error": error,
                "form_data": form_data or {},
                "search_data": search_data or {},
            },
        )

    # =========================================================
    # STEP 1: FIND APPLICANT
    # =========================================================

    if request.method == "POST" and request.POST.get("action") == "find_applicant":

        lastname = request.POST.get("lastname", "").strip()
        firstname = request.POST.get("firstname", "").strip()
        middlename = request.POST.get("middlename", "").strip()
        birthdate_input = request.POST.get("birthdate", "").strip()

        search_data = request.POST

        if not lastname:
            return render_page(
                error="Please enter the last name.",
                form_data=search_data,
                search_data=search_data,
            )

        if not firstname:
            return render_page(
                error="Please enter the first name.",
                form_data=search_data,
                search_data=search_data,
            )

        if not birthdate_input:
            return render_page(
                error="Please enter your date of birth.",
                form_data=search_data,
                search_data=search_data,
            )

        birthdate = parse_date(birthdate_input)

        if not birthdate:
            return render_page(
                error="Please enter a valid date of birth.",
                form_data=search_data,
                search_data=search_data,
            )

        # Middle name is optional.
        applicant_query = Applicant.objects.filter(
            lastname__iexact=lastname,
            firstname__iexact=firstname,
            birthdate=birthdate,
        )

        if middlename:
            applicant_query = applicant_query.filter(
                middlename__iexact=middlename
            )
        else:
            applicant_query = applicant_query.filter(
                Q(middlename__isnull=True) | Q(middlename="")
            )

        matching_applicants = list(applicant_query[:2])

        if not matching_applicants:
            return render_page(
                error=(
                    "No registration record was found using the "
                    "information provided. Please check your details."
                ),
                form_data=search_data,
                search_data=search_data,
            )

        if len(matching_applicants) > 1:
            return render_page(
                error=(
                    "More than one record matched these details. "
                    "Please enter your middle name and try again."
                ),
                form_data=search_data,
                search_data=search_data,
            )

        applicant = matching_applicants[0]

        # Check for an existing request awaiting review.
        existing_request = ApplicantUpdateRequest.objects.filter(
            applicant=applicant,
            status__in=["PENDING", "REVIEW"],
        ).exists()

        if existing_request:
            return render_page(
                applicant=applicant,
                error=(
                    "This applicant already has an update or "
                    "correction request pending review."
                ),
            )

        return render_page(applicant=applicant)

    # =========================================================
    # STEP 2: SUBMIT UPDATE / CORRECTION REQUEST
    # =========================================================

    if request.method == "POST" and request.POST.get("action") == "submit_update":

        applicant_id = request.POST.get("applicant_id", "").strip()

        if not applicant_id:
            return render_page(
                error="Applicant record was not found.",
                form_data=request.POST,
            )

        applicant = get_object_or_404(
            Applicant,
            id=applicant_id,
        )

        form_data = request.POST

        # -----------------------------------------------------
        # READ FORM FIELDS
        # -----------------------------------------------------

        lastname = request.POST.get("lastname", "").strip()
        firstname = request.POST.get("firstname", "").strip()
        middlename = request.POST.get("middlename", "").strip()
        age_input = request.POST.get("age", "").strip()
        sex = request.POST.get("sex", "").strip()
        birthdate_input = request.POST.get("birthdate", "").strip()
        birthplace = request.POST.get("birthplace", "").strip()

        # The template sends brgy_id.
        brgy_id = request.POST.get("brgy_id", "").strip()

        province = request.POST.get("province", "Albay").strip()
        municipality = request.POST.get("municipality", "Pio Duran").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()

        civil_status = request.POST.get("civil_status", "").strip()

        pwd_status = request.POST.get("pwd_status", "NO").strip()
        citizenship_status = request.POST.get(
            "citizenship_status",
            "BY_BIRTH",
        ).strip()

        father = request.POST.get("father", "").strip()
        mother = request.POST.get("mother", "").strip()
        reason = request.POST.get("reason", "").strip()

        # Read the uploaded file from request.FILES.
        valid_id_document = request.FILES.get("valid_id_document")

        # -----------------------------------------------------
        # REQUIRED FIELD VALIDATION
        # -----------------------------------------------------

        required_fields = {
            "Last name": lastname,
            "First name": firstname,
            "Age": age_input,
            "Sex": sex,
            "Birthdate": birthdate_input,
            "Birthplace": birthplace,
            "Barangay": brgy_id,
            "Province": province,
            "Municipality": municipality,
            "Phone": phone,
            "Email": email,
            "Father's name": father,
            "Mother's name": mother,
            "Reason": reason,
        }

        for field_name, value in required_fields.items():
            if not value:
                return render_page(
                    applicant=applicant,
                    error=f"{field_name} is required.",
                    form_data=form_data,
                )

        # -----------------------------------------------------
        # CIVIL STATUS VALIDATION
        # -----------------------------------------------------

        allowed_civil_statuses = {
            "SINGLE",
            "MARRIED",
            "WIDOWED",
            "SEPARATED",
        }

        if civil_status and civil_status not in allowed_civil_statuses:
            return render_page(
                applicant=applicant,
                error="Please select a valid civil status.",
                form_data=form_data,
            )

        # -----------------------------------------------------
        # AGE VALIDATION
        # -----------------------------------------------------

        try:
            applicant_age = int(age_input)
        except (ValueError, TypeError):
            return render_page(
                applicant=applicant,
                error="Please enter a valid age.",
                form_data=form_data,
            )

        if not 1 <= applicant_age <= 150:
            return render_page(
                applicant=applicant,
                error="Age must be between 1 and 150.",
                form_data=form_data,
            )

        # -----------------------------------------------------
        # BIRTHDATE VALIDATION
        # -----------------------------------------------------

        birthdate = parse_date(birthdate_input)

        if not birthdate:
            return render_page(
                applicant=applicant,
                error="Please enter a valid birthdate.",
                form_data=form_data,
            )

        if birthdate > __import__("datetime").date.today():
            return render_page(
                applicant=applicant,
                error="Birthdate cannot be in the future.",
                form_data=form_data,
            )

        # -----------------------------------------------------
        # SEX VALIDATION
        # -----------------------------------------------------

        if sex not in {"MALE", "FEMALE"}:
            return render_page(
                applicant=applicant,
                error="Please select a valid sex.",
                form_data=form_data,
            )

        # -----------------------------------------------------
        # PHONE VALIDATION
        # -----------------------------------------------------

        if not phone.isdigit() or len(phone) != 11:
            return render_page(
                applicant=applicant,
                error="Please enter a valid 11-digit mobile number.",
                form_data=form_data,
            )

        if not phone.startswith("09"):
            return render_page(
                applicant=applicant,
                error="Please enter a valid Philippine mobile number beginning with 09.",
                form_data=form_data,
            )

        # -----------------------------------------------------
        # EMAIL VALIDATION
        # -----------------------------------------------------

        try:
            validate_email(email)
        except ValidationError:
            return render_page(
                applicant=applicant,
                error="Please enter a valid email address.",
                form_data=form_data,
            )

        # -----------------------------------------------------
        # REASON VALIDATION
        # -----------------------------------------------------

        if len(reason) < 5:
            return render_page(
                applicant=applicant,
                error="Please provide a more detailed reason for your request.",
                form_data=form_data,
            )

        if len(reason) > 2000:
            return render_page(
                applicant=applicant,
                error="The reason must not exceed 2,000 characters.",
                form_data=form_data,
            )

        # -----------------------------------------------------
        # PWD AND CITIZENSHIP VALIDATION
        # -----------------------------------------------------

        if pwd_status not in {"YES", "NO"}:
            return render_page(
                applicant=applicant,
                error="Please select a valid PWD status.",
                form_data=form_data,
            )

        if citizenship_status not in {"BY_BIRTH", "NATURALIZED"}:
            return render_page(
                applicant=applicant,
                error="Please select a valid citizenship status.",
                form_data=form_data,
            )

        # -----------------------------------------------------
        # VALID ID / SUPPORTING DOCUMENT VALIDATION
        # -----------------------------------------------------

        if not valid_id_document:
            return render_page(
                applicant=applicant,
                error="Please upload a valid ID or supporting document.",
                form_data=form_data,
            )

        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
        max_file_size = 5 * 1024 * 1024  # 5 MB

        file_extension = os.path.splitext(
            valid_id_document.name
        )[1].lower()

        if file_extension not in allowed_extensions:
            return render_page(
                applicant=applicant,
                error="Invalid document format. Upload PDF, JPG, JPEG, or PNG only.",
                form_data=form_data,
            )

        if valid_id_document.size == 0:
            return render_page(
                applicant=applicant,
                error="The uploaded document is empty.",
                form_data=form_data,
            )

        if valid_id_document.size > max_file_size:
            return render_page(
                applicant=applicant,
                error="The uploaded document must not exceed 5 MB.",
                form_data=form_data,
            )

        # -----------------------------------------------------
        # CHECK BARANGAY
        # -----------------------------------------------------

        try:
            barangay = Barangay.objects.get(id=brgy_id)
        except (Barangay.DoesNotExist, ValueError, TypeError):
            return render_page(
                applicant=applicant,
                error="The selected barangay does not exist.",
                form_data=form_data,
            )

        # -----------------------------------------------------
        # DUPLICATE NAME CHECK
        # -----------------------------------------------------

        duplicate_name_query = Applicant.objects.filter(
            lastname__iexact=lastname,
            firstname__iexact=firstname,
            middlename__iexact=middlename,
        ).exclude(id=applicant.id)

        if duplicate_name_query.exists():
            return render_page(
                applicant=applicant,
                error=(
                    "Another applicant with the same last name, "
                    "first name, and middle name already exists."
                ),
                form_data=form_data,
            )

        # -----------------------------------------------------
        # DUPLICATE EMAIL CHECK
        # -----------------------------------------------------

        duplicate_email = Applicant.objects.filter(
            email__iexact=email,
        ).exclude(
            id=applicant.id,
        ).exists()

        if duplicate_email:
            return render_page(
                applicant=applicant,
                error="Another applicant with this email address already exists.",
                form_data=form_data,
            )

        # -----------------------------------------------------
        # CHECK EXISTING PENDING REQUEST
        # -----------------------------------------------------

        existing_request = ApplicantUpdateRequest.objects.filter(
            applicant=applicant,
            status__in=["PENDING", "REVIEW"],
        ).exists()

        if existing_request:
            return render_page(
                applicant=applicant,
                error=(
                    "This applicant already has an update or "
                    "correction request pending review."
                ),
                form_data=form_data,
            )

        # -----------------------------------------------------
        # CREATE UPDATE REQUEST
        # -----------------------------------------------------

        update_request = ApplicantUpdateRequest.objects.create(
            applicant=applicant,

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

            # Requires a civil_status field on ApplicantUpdateRequest.
            civil_status=civil_status,

            pwd_status=pwd_status,
            citizenship_status=citizenship_status,

            father=father,
            mother=mother,

            reason=reason,

            # Requires a FileField on ApplicantUpdateRequest.
            valid_id_document=valid_id_document,

            status="PENDING",
        )

        return redirect(
            "update-success",
            request_id=update_request.id,
        )

    # =========================================================
    # FIRST PAGE
    # =========================================================

    return render_page()


def update_success(request, request_id):

    update_request = get_object_or_404(
        ApplicantUpdateRequest,
        id=request_id
    )

    return render(
        request,
        "components/update_success.html",
        {
            "update_request": update_request,
        }
    )


def transfer_registration(request):
    template_name = "applicant/forms/transfer_registration.html"
    barangays = Barangay.objects.all().order_by("name")

    def render_page(applicant=None, error=None, search_data=None, form_data=None):
        return render(
            request,
            template_name,
            {
                "applicant": applicant,
                "barangays": barangays,
                "error": error,
                "search_data": search_data or {},
                "form_data": form_data or {},
            },
        )

    # =========================================================
    # STEP 1: FIND APPLICANT
    # =========================================================
    if (
        request.method == "POST"
        and request.POST.get("action") == "find_applicant"
    ):
        lastname = request.POST.get("lastname", "").strip()
        firstname = request.POST.get("firstname", "").strip()
        middlename = request.POST.get("middlename", "").strip()
        birthdate_input = request.POST.get("birthdate", "").strip()

        if not lastname:
            return render_page(
                error="Please enter the last name.",
                search_data=request.POST,
            )

        if not firstname:
            return render_page(
                error="Please enter the first name.",
                search_data=request.POST,
            )

        if not birthdate_input:
            return render_page(
                error="Please enter the birthdate.",
                search_data=request.POST,
            )

        birthdate = parse_date(birthdate_input)

        if not birthdate:
            return render_page(
                error="Please enter a valid birthdate.",
                search_data=request.POST,
            )

        applicant_query = Applicant.objects.filter(
            lastname__iexact=lastname,
            firstname__iexact=firstname,
            birthdate=birthdate,
        )

        if middlename:
            applicant_query = applicant_query.filter(
                middlename__iexact=middlename,
            )
        else:
            applicant_query = applicant_query.filter(
                Q(middlename__isnull=True) | Q(middlename=""),
            )

        matches = list(applicant_query[:2])

        if not matches:
            return render_page(
                error=(
                    "No registration record was found using the "
                    "information provided. Check your details and try again."
                ),
                search_data=request.POST,
            )

        if len(matches) > 1:
            return render_page(
                error=(
                    "Multiple registration records match those details. "
                    "Please enter your middle name and try again."
                ),
                search_data=request.POST,
            )

        applicant = matches[0]

        existing_request = ApplicantTransferRequest.objects.filter(
            applicant=applicant,
            status__in=["PENDING", "REVIEW"],
        ).exists()

        if existing_request:
            return render_page(
                applicant=applicant,
                error=(
                    "This applicant already has a transfer request "
                    "pending review."
                ),
            )

        return render_page(applicant=applicant)

    # =========================================================
    # STEP 2: SUBMIT TRANSFER REQUEST
    # =========================================================
    if (
        request.method == "POST"
        and request.POST.get("action") == "submit_transfer"
    ):
        applicant_id = request.POST.get("applicant_id", "").strip()

        if not applicant_id:
            return render_page(
                error="Applicant record was not found. Please search again.",
                form_data=request.POST,
            )

        applicant = get_object_or_404(
            Applicant,
            id=applicant_id,
        )

        new_brgy_id = request.POST.get("new_brgy", "").strip()
        new_municipality = request.POST.get(
            "new_municipality", ""
        ).strip()
        new_province = request.POST.get(
            "new_province", ""
        ).strip()
        reason = request.POST.get("reason", "").strip()

        # Get uploaded ID document.
        valid_id_document = request.FILES.get("valid_id_document")

        def show_error(message):
            return render_page(
                applicant=applicant,
                error=message,
                form_data=request.POST,
            )

        # -----------------------------------------------------
        # REQUIRED FIELDS
        # -----------------------------------------------------
        required_fields = {
            "New barangay": new_brgy_id,
            "New municipality": new_municipality,
            "New province": new_province,
            "Reason for transfer": reason,
        }

        for field_name, value in required_fields.items():
            if not value:
                return show_error(f"{field_name} is required.")

        if len(reason) < 5:
            return show_error(
                "Please provide a more detailed reason for the transfer."
            )

        if len(reason) > 2000:
            return show_error(
                "The reason must not exceed 2,000 characters."
            )

        # -----------------------------------------------------
        # VALIDATE UPLOADED VALID ID
        # -----------------------------------------------------
        if not valid_id_document:
            return show_error(
                "Please upload a valid ID before submitting your request."
            )

        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}

        file_extension = os.path.splitext(
            valid_id_document.name
        )[1].lower()

        if file_extension not in allowed_extensions:
            return show_error(
                "Invalid ID file format. Upload a PDF, JPG, JPEG, or PNG file."
            )

        max_file_size = 5 * 1024 * 1024  # 5 MB

        if valid_id_document.size > max_file_size:
            return show_error(
                "The uploaded valid ID must not exceed 5 MB."
            )

        # -----------------------------------------------------
        # VALIDATE NEW BARANGAY
        # -----------------------------------------------------
        try:
            new_barangay = Barangay.objects.get(id=new_brgy_id)
        except (Barangay.DoesNotExist, ValueError, TypeError):
            return show_error(
                "The selected barangay does not exist."
            )

        # -----------------------------------------------------
        # PREVENT SAME ADDRESS
        # -----------------------------------------------------
        current_barangay_id = applicant.brgy_id

        same_barangay = (
            current_barangay_id is not None
            and current_barangay_id == new_barangay.id
        )

        same_municipality = (
            (applicant.municipality or "").strip().casefold()
            == new_municipality.casefold()
        )

        same_province = (
            (applicant.province or "").strip().casefold()
            == new_province.casefold()
        )

        if same_barangay and same_municipality and same_province:
            return show_error(
                "The new address is the same as your current "
                "registration address."
            )

        # -----------------------------------------------------
        # CHECK FOR EXISTING REQUEST AGAIN
        # -----------------------------------------------------
        existing_request = ApplicantTransferRequest.objects.filter(
            applicant=applicant,
            status__in=["PENDING", "REVIEW"],
        ).exists()

        if existing_request:
            return show_error(
                "This applicant already has a transfer request "
                "pending review."
            )

        # -----------------------------------------------------
        # SAVE TRANSFER REQUEST AND UPLOADED ID
        # -----------------------------------------------------
        transfer_request = ApplicantTransferRequest.objects.create(
            applicant=applicant,
            current_brgy=applicant.brgy,
            new_brgy=new_barangay,
            current_municipality=applicant.municipality or "Pio Duran",
            current_province=applicant.province or "Albay",
            new_municipality=new_municipality,
            new_province=new_province,
            reason=reason,
            valid_id_document=valid_id_document,
            status="PENDING",
        )

        return redirect(
            "transfer-success",
            request_id=transfer_request.id,
        )

    # =========================================================
    # INITIAL PAGE
    # =========================================================
    return render_page()


def transfer_success(request, request_id):

    transfer_request = get_object_or_404(
        ApplicantTransferRequest,
        id=request_id
    )

    return render(
        request,
        "components/transfer_success.html",
        {
            "transfer_request": transfer_request,
        }
    )


def reactivate_registration(request):
    template_name = "applicant/forms/reactivation_registration.html"
    max_file_size = 5 * 1024 * 1024  # 5 MB

    allowed_extensions = {
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
    }

    def render_page(applicant=None, error=None,
                    search_data=None, form_data=None):
        return render(
            request,
            template_name,
            {
                "applicant": applicant,
                "error": error,
                "search_data": search_data or {},
                "form_data": form_data or {},
            },
        )

    # =====================================================
    # STEP 1: FIND APPLICANT
    # =====================================================

    if (
        request.method == "POST"
        and request.POST.get("action") == "find_applicant"
    ):
        lastname = request.POST.get("lastname", "").strip()
        firstname = request.POST.get("firstname", "").strip()
        middlename = request.POST.get("middlename", "").strip()
        birthdate_input = request.POST.get("birthdate", "").strip()

        if not lastname:
            return render_page(
                error="Please enter the last name.",
                search_data=request.POST,
            )

        if not firstname:
            return render_page(
                error="Please enter the first name.",
                search_data=request.POST,
            )

        if not middlename:
            return render_page(
                error="Please enter the middle name.",
                search_data=request.POST,
            )

        if not birthdate_input:
            return render_page(
                error="Please enter the birthdate.",
                search_data=request.POST,
            )

        birthdate = parse_date(birthdate_input)

        if not birthdate:
            return render_page(
                error="Please enter a valid birthdate.",
                search_data=request.POST,
            )

        applicant = Applicant.objects.filter(
            lastname__iexact=lastname,
            firstname__iexact=firstname,
            middlename__iexact=middlename,
            birthdate=birthdate,
        ).first()

        if not applicant:
            return render_page(
                error=(
                    "No registration record was found using "
                    "the information provided. Please check "
                    "your details and try again."
                ),
                search_data=request.POST,
            )

        # An active applicant does not need reactivation.
        if applicant.is_active:
            return render_page(
                applicant=applicant,
                error=(
                    "This applicant is already active. "
                    "A reactivation request is not necessary."
                ),
            )

        # Check for an existing request awaiting review.
        existing_request = (
            ApplicantReactivationRequest.objects.filter(
                applicant=applicant,
                status__in=["PENDING", "REVIEW"],
            ).exists()
        )

        if existing_request:
            return render_page(
                applicant=applicant,
                error=(
                    "This applicant already has a reactivation "
                    "request pending review."
                ),
            )

        return render_page(applicant=applicant)

    # =====================================================
    # STEP 2: SUBMIT REACTIVATION REQUEST
    # =====================================================

    if (
        request.method == "POST"
        and request.POST.get("action") == "submit_reactivation"
    ):
        applicant_id = request.POST.get("applicant_id", "").strip()

        if not applicant_id:
            return render_page(
                error="Applicant record was not found. Please search again.",
                form_data=request.POST,
            )

        applicant = get_object_or_404(
            Applicant,
            id=applicant_id,
        )

        # Check active status again before accepting submission.
        if applicant.is_active:
            return render_page(
                applicant=applicant,
                error=(
                    "This applicant is already active. "
                    "A reactivation request is not necessary."
                ),
                form_data=request.POST,
            )

        reason = request.POST.get("reason", "").strip()
        valid_id_document = request.FILES.get("valid_id_document")

        if not reason:
            return render_page(
                applicant=applicant,
                error="Please provide the reason for reactivation.",
                form_data=request.POST,
            )

        if len(reason) < 5:
            return render_page(
                applicant=applicant,
                error="Please provide a more detailed reason (at least 5 characters).",
                form_data=request.POST,
            )

        if len(reason) > 2000:
            return render_page(
                applicant=applicant,
                error="The reason must not exceed 2,000 characters.",
                form_data=request.POST,
            )

        # -------------------------------------------------
        # VALIDATE REQUIRED VALID ID
        # -------------------------------------------------

        if not valid_id_document:
            return render_page(
                applicant=applicant,
                error="Please upload a copy of your valid ID.",
                form_data=request.POST,
            )

        file_extension = Path(valid_id_document.name).suffix.lower()

        if file_extension not in allowed_extensions:
            return render_page(
                applicant=applicant,
                error="Invalid file type. Upload a PDF, JPG, JPEG, or PNG file.",
                form_data=request.POST,
            )

        if valid_id_document.size > max_file_size:
            return render_page(
                applicant=applicant,
                error="The valid ID file must not exceed 5 MB.",
                form_data=request.POST,
            )

        # -------------------------------------------------
        # CHECK FOR EXISTING REQUEST AGAIN
        # -------------------------------------------------

        existing_request = (
            ApplicantReactivationRequest.objects.filter(
                applicant=applicant,
                status__in=["PENDING", "REVIEW"],
            ).exists()
        )

        if existing_request:
            return render_page(
                applicant=applicant,
                error=(
                    "This applicant already has a reactivation "
                    "request pending review."
                ),
                form_data=request.POST,
            )

        # -------------------------------------------------
        # SAVE REQUEST AND UPLOADED ID
        # -------------------------------------------------

        reactivation_request = ApplicantReactivationRequest.objects.create(
            applicant=applicant,
            reason=reason,
            valid_id_document=valid_id_document,
            status="PENDING",
        )

        return redirect(
            "reactivation-success",
            request_id=reactivation_request.id,
        )

    # =====================================================
    # FIRST PAGE
    # =====================================================

    return render_page()



def reactivation_success(request, request_id):

    reactivation_request = get_object_or_404(
        ApplicantReactivationRequest,
        id=request_id
    )

    return render(
        request,
        "components/reactivation_success.html",
        {
            "reactivation_request": reactivation_request,
        }
    )


def reinstate_registration(request):
    template_name = "applicant/forms/reinstatement_registration.html"

    # =========================================================
    # STEP 1: FIND APPLICANT
    # =========================================================

    if (
        request.method == "POST"
        and request.POST.get("action") == "find_applicant"
    ):
        lastname = request.POST.get("lastname", "").strip()
        firstname = request.POST.get("firstname", "").strip()
        middlename = request.POST.get("middlename", "").strip()
        birthdate_input = request.POST.get("birthdate", "").strip()

        search_data = request.POST

        if not lastname:
            return render(request, template_name, {
                "error": "Please enter the last name.",
                "search_data": search_data,
            })

        if not firstname:
            return render(request, template_name, {
                "error": "Please enter the first name.",
                "search_data": search_data,
            })

        if not middlename:
            return render(request, template_name, {
                "error": "Please enter the middle name.",
                "search_data": search_data,
            })

        birthdate = parse_date(birthdate_input)

        if not birthdate:
            return render(request, template_name, {
                "error": "Please enter a valid birthdate.",
                "search_data": search_data,
            })

        # Find the existing registration
        applicant = Applicant.objects.filter(
            lastname__iexact=lastname,
            firstname__iexact=firstname,
            middlename__iexact=middlename,
            birthdate=birthdate,
        ).first()

        if not applicant:
            return render(request, template_name, {
                "error": (
                    "No registration record was found "
                    "using the information provided."
                ),
                "search_data": search_data,
            })

        # An active applicant normally does not need reinstatement.
        if applicant.is_active:
            return render(request, template_name, {
                "error": (
                    "This registration is already active. "
                    "A reinstatement request cannot be submitted."
                ),
                "search_data": search_data,
            })

        # Prevent duplicate pending or in-review requests
        existing_request = (
            ApplicantReinstatementRequest.objects.filter(
                applicant=applicant,
                status__in=["PENDING", "REVIEW"],
            ).exists()
        )

        if existing_request:
            return render(request, template_name, {
                "applicant": applicant,
                "error": (
                    "This applicant already has a reinstatement "
                    "request pending review."
                ),
            })

        return render(request, template_name, {
            "applicant": applicant,
        })

    # =========================================================
    # STEP 2: SUBMIT REINSTATEMENT REQUEST
    # =========================================================

    if (
        request.method == "POST"
        and request.POST.get("action") == "submit_reinstatement"
    ):
        applicant_id = request.POST.get("applicant_id", "").strip()

        if not applicant_id:
            return render(request, template_name, {
                "error": "Applicant record was not found.",
                "form_data": request.POST,
            })

        applicant = get_object_or_404(
            Applicant,
            id=applicant_id,
        )

        reason = request.POST.get("reason", "").strip()
        valid_id_document = request.FILES.get("valid_id_document")

        # =====================================================
        # VALIDATE APPLICANT STATUS
        # =====================================================

        if applicant.is_active:
            return render(request, template_name, {
                "applicant": applicant,
                "error": (
                    "This registration is already active. "
                    "A reinstatement request cannot be submitted."
                ),
                "form_data": request.POST,
            })

        # =====================================================
        # VALIDATE REASON
        # =====================================================

        if not reason:
            return render(request, template_name, {
                "applicant": applicant,
                "error": (
                    "Please provide the reason "
                    "for reinstatement."
                ),
                "form_data": request.POST,
            })

        if len(reason) < 5:
            return render(request, template_name, {
                "applicant": applicant,
                "error": (
                    "The reason must contain at least "
                    "5 characters."
                ),
                "form_data": request.POST,
            })

        if len(reason) > 2000:
            return render(request, template_name, {
                "applicant": applicant,
                "error": (
                    "The reason must not exceed "
                    "2,000 characters."
                ),
                "form_data": request.POST,
            })

        # =====================================================
        # VALIDATE VALID ID DOCUMENT
        # =====================================================

        if not valid_id_document:
            return render(request, template_name, {
                "applicant": applicant,
                "error": "Please upload a valid ID document.",
                "form_data": request.POST,
            })

        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
        file_extension = Path(valid_id_document.name).suffix.lower()

        if file_extension not in allowed_extensions:
            return render(request, template_name, {
                "applicant": applicant,
                "error": (
                    "Invalid ID file format. Upload a PDF, "
                    "JPG, JPEG, or PNG file."
                ),
                "form_data": request.POST,
            })

        max_file_size = 5 * 1024 * 1024  # 5 MB

        if valid_id_document.size > max_file_size:
            return render(request, template_name, {
                "applicant": applicant,
                "error": (
                    "The ID document must not exceed 5 MB."
                ),
                "form_data": request.POST,
            })

        # =====================================================
        # CHECK EXISTING REQUEST AGAIN
        # =====================================================

        existing_request = (
            ApplicantReinstatementRequest.objects.filter(
                applicant=applicant,
                status__in=["PENDING", "REVIEW"],
            ).exists()
        )

        if existing_request:
            return render(request, template_name, {
                "applicant": applicant,
                "error": (
                    "This applicant already has a reinstatement "
                    "request pending review."
                ),
                "form_data": request.POST,
            })

        # =====================================================
        # CREATE REINSTATEMENT REQUEST
        # =====================================================

        reinstatement_request = (
            ApplicantReinstatementRequest.objects.create(
                applicant=applicant,
                reason=reason,
                valid_id_document=valid_id_document,
                status="PENDING",
            )
        )

        return redirect(
            "reinstatement-success",
            request_id=reinstatement_request.id,
        )

    # =========================================================
    # FIRST PAGE
    # =========================================================

    return render(request, template_name)


def reinstatement_success(request, request_id):

    reinstatement_request = get_object_or_404(
        ApplicantReinstatementRequest,
        id=request_id
    )

    return render(
        request,
        "components/reinstatement_success.html",
        {
            "reinstatement_request": reinstatement_request,
        }
    )