# flake8: noqa: E501
# fmt: off
class SampleQuestionBank:
    """A collection of sample questions for testing purposes."""

    def __init__(self):
        self.questions = []
        # Append data as tuples: (id, text) just to make it easier to read for users.
        self.questions.append((0, "can a prescribed item have more than one endorsement or is it expected that a single item has no more than one endorsement?"))  # noqa: E501
        self.questions.append((1, "for the non-repudiation screen, Note - is this the note to pharmacy? note to patient?"))  # noqa: E501
        self.questions.append((2, """We are getting an error from DSS "Unauthorised". We have checked the credentials and they appear to be correct. What could be the cause? Note that, the CIS2 key is different to the key used in the EPS application (which has the signing api attached to it)"""))  # noqa: E501
        self.questions.append((3, """Can you clarify this requirement?

"The connecting system must monitor the sending of prescription order request and alert the NHSE service desk if requests fail to send as expected"a)Is this meant to be an automated process, or should an option be given to the user to send an e-mail?
b)What will be the e-mail used?
c)Any certain format needed for the report?
d)Should this be done only after 2 hours of retries that failed?"""))  # noqa: E501
        self.questions.append((4, "how do we find if a patient is a cross-border patient?"))  # noqa: E501
        self.questions.append((5, "When a prescription has only one prescribed item and the prescriber cancels the prescribed item will the prescription be downloaded when a bulk download request is made to /FHIR/R4/Task/$release?"))  # noqa: E501
        self.questions.append((6, "When I have authenticated with a smartcard using CIS2 over an HSCN connection what happens when the smartcard is removed?"))  # noqa: E501
        self.questions.append((7, "direct me to the web page that has the details on how to uninstall Oberthur SR1"))  # noqa: E501
        self.questions.append((8, """Should the Dispensing system send a Claim notification message when all the prescription items on the prescription have expired, and if it should then what value should be sent for the overall prescription form status for the FHIAR API extension "https://fhir.nhs.uk/StructureDefinition/Extension-EPS-TaskBusinessStatus"?"""))  # noqa: E501
        self.questions.append((9, """For an EPS FHIR API Dispense Notification message, when should the value "on-hold" be used for resource: { "resourceType": "MedicationDispense", "status"} for a prescription item ?"""))  # noqa: E501
        self.questions.append((10, "confirm if dispensing systems are required to include an option for the user to select the MedicationDispenseReasoncodes of 004, 005, and 009"))  # noqa: E501
        self.questions.append((11, "how many lines can a prescription have?"))  # noqa: E501
        self.questions.append((12, "Is extension:controlledDrugSchedule.value.userSelected. used for EPS?"))  # noqa: E501
        self.questions.append((13, "Can we use dosageInstruction.timing.repeat.boundsPeriod.start or ...dosageInstruction.timing.repeat.boundsPeriod.end?"))  # noqa: E501
        self.questions.append((14, "show me example of prescription successfully created response within the Electronic Prescribing System (EPS), where a unique identifier for the prescription, often referred to as the prescription ID is shown"))  # noqa: E501
        self.questions.append((15, "please provide a documentation link where i find the specific format of prescribing token?"))         # noqa: E501
        self.questions.append((16, """I have a query related to cancelling Repeat Dispensing (RD) courses. We would like to know what the Spine allows in terms of cancelling particular issues of a RD course.For example, let's say a patient has an ongoing RD course which originally had 6 issues. Let's say that issue 1 has been dispensed (status 'Dispensed'), and issue 2 has been pulled down from the Spine by the pharmacist (status 'With dispenser'). The remaining issues 3-6 are still on spine.Can the 'Cancel' request sent to Spine handle the following scenarios? And what will happen if so?

Doctor requests to cancel all issues, 1-6
Doctor requests to cancel all remaining issues on Spine, 3-6"""))  # noqa: E501
        self.questions.append((17, "Does a Cancel request for a medication that has been downloaded include the pharmacy details of the pharmacy that had downloaded the medication in the response"))  # noqa: E501
        self.questions.append((18, """For MedicationRequest "entry. resource. groupIdentifier. extension. valueIdentifier" what is the Long-form Prescription ID?"""))  # noqa: E501
        self.questions.append((19, "for the non-repudiation screen, do we use the patient friendly text for dosage information?"))  # noqa: E501
        self.questions.append((20, "Can an API have multiple callback URLs"))  # noqa: E501

    def get_questions(self, start: int, end: int) -> list[tuple[int, str]]:
        """
        Pulls a selection of questions
        """
        # Must be integers
        if not isinstance(start, int):
            raise TypeError(f"'start' must be an integer, got {type(start).__name__}")
        
        if not isinstance(end, int):
            raise TypeError(f"'end' must be an integer, got {type(end).__name__}")

        # Must be in valid range
        if start < 0:
            raise ValueError("'start' cannot be negative")
        
        if end < 0 or end < start:
            raise ValueError("'end' must be non-negative and greater than or equal to 'start'")

        # Extract only the text (index 1) from the tuple
        return list(self.questions[start : end + 1])

    def add_questions(self, question_text: str):
        self.questions.append((len(self.questions), question_text))
