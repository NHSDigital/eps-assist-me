SCAL Requirement 1.1.1 User authentication and information governance: Dispensers can authenticate themselves through the Care Identity Service using their smartcard.   This lets dispensers access Spine services like EPS. related info: Care Identity Service

SCAL Requirement 1.1.2 User authentication and information governance: Role-based access controls (RBAC) must be used to limit what dispensers can and cannot do.   RBAC rules are in the National RBAC Database. related info: RBAC Implementation  Guidance for EPS

SCAL Requirement 1.1.3 User authentication and information governance: If a user is authenticated with the virtual "National Locum Pharmacy" ODS code, FFFFF, then the system must display the following to the user following successful authentication:  âYou are accountable to the pharmacy organisation in which you are currently working for all the actions you take on the system; you may not use the system to act in any other capacityâ.

SCAL Requirement 1.2.1 Populate details of the dispenser in user-restricted EPS messages: All user-restricted messages sent to EPS must contain the dispenser's SDS user identifier.

SCAL Requirement 1.2.2 Populate details of the dispenser in user-restricted EPS messages: All user-restricted messages sent to EPS must contain the dispenser's SDS role profile identifier.

SCAL Requirement 1.2.3 Populate details of the dispenser in user-restricted EPS messages: All user-restricted messages sent to EPS must contain the dispenser's SDS job role code.

SCAL Requirement 1.2.4 Populate details of the dispenser in user-restricted EPS messages: All user-restricted messages sent to EPS must contain the dispenser's name.

SCAL Requirement 1.2.5 Populate details of the dispenser in user-restricted EPS messages: All user-restricted messages sent to EPS must contain the dispenser's telephone number.  This may be the same as the organisation's telephone number.

SCAL Requirement 1.2.6a Populate details of the dispenser in user-restricted EPS messages: For suppliers developing an English Dispensing System:  All user-restricted messages sent to EPS must contain the dispensing site's ODS code. related info: If developing for both England and Wales 1.2.6a and 1.2.6b will need to answered.

SCAL Requirement 1.2.6b Populate details of the dispenser in user-restricted EPS messages: For suppliers developing an Welsh Dispensing System:  When supporting Welsh Pharmacies, a 7-digit ODS code may also be retained within the local system. related info: If developing for both England and Wales 1.2.6a and 1.2.6b will need to answered.

SCAL Requirement 1.2.7 Populate details of the dispenser in user-restricted EPS messages: All user-restricted messages sent to EPS must contain the dispensing site's name.

SCAL Requirement 1.2.8 Populate details of the dispenser in user-restricted EPS messages: All user-restricted messages sent to EPS must contain the dispensing site's telephone number.

SCAL Requirement 1.2.9 Populate details of the dispenser in user-restricted EPS messages: All user-restricted messages sent to EPS must contain the dispensing site's address.

SCAL Requirement 1.3.1 Nominate a dispensing site on behalf of the patient: Dispensers must be able to see all current nominations for the patient. They must be able to see the nominated dispensing site's:  â¢ ODS code â¢ contractor type â¢ organisation name â¢ organisation address â¢ organisation postcode related info: PDS

SCAL Requirement 1.3.2 Nominate a dispensing site on behalf of the patient: Dispensers must use the Electronic Transmission Prescriptions (ETP) Web Services Directory of Services (DOS) API to find valid dispensing sites for the patient. related info: ETP Web Services DOS API

SCAL Requirement 1.3.3 Nominate a dispensing site on behalf of the patient: Dispensers must be able to add, update, or remove a patient's P1 or P2 nomination on the Personal Demographics Service (PDS) at the patient's request.   Dispensers must only be able to remove a P3 dispensing doctor nomination, not add or update it. related info: PDS

SCAL Requirement 1.3.4 Nominate a dispensing site on behalf of the patient: All ODS codes for a nomination must be in uppercase. related info: PDS

SCAL Requirement 1.3.5 Nominate a dispensing site on behalf of the patient: All manual entries of ODS codes for a dispensing site must be validated using ETP Web Services DOS API. related info: ETP Web Services DOS API

SCAL Requirement 1.4.1 Create and maintain patient medical records: The dispensing system must maintain a local database of electronic prescriptions received from EPS.

SCAL Requirement 1.4.2 Create and maintain patient medical records: The dispensing system must maintain a local database of patient demographic information.

SCAL Requirement 1.4.3 Create and maintain patient medical records: The dispensing system must use the NHS number as the patient identifier. This can be found on the electronic prescription and PDS. related info: PDS

SCAL Requirement 1.4.4 Create and maintain patient medical records: The dispensing system must have an effective back up and disaster recovery process.

SCAL Requirement 1.4.5 Create and maintain patient medical records: When electronic prescriptions are received from Spine, the system must match them to a local patient record.   Where the patient's details can be matched, this should be treated as a full match and require no user intervention. The details to match are the patient's:  â¢ NHS number â¢ full name (including prefixes and suffixes) â¢ date of birth â¢ address (all lines) â¢ postcode â¢ gender   Where a full match is not possible and the prescription could be matched to a number of local patient records, then the dispenser must be alerted and select the correct local patient record.  Where the prescription cannot be matched to any local patient record, then the dispenser must be able to manually create a new patient record.

SCAL Requirement 1.5.1 Release a prescription for a patient or a dispensing site: When the release request is for a specific prescription, the short-form prescription ID must be stated.

SCAL Requirement 1.5.2 Release a prescription for a patient or a dispensing site: The system must be able to read and interpret the barcode on a prescription token. The barcode will use the Code 128 standard.  The system must also support the manual entry of a prescription ID.

SCAL Requirement 1.5.3 Release a prescription for a patient or a dispensing site: Prescriptions released through unattended access must be "locked" in the dispensing system. Only the prescription ID and the prescribing date must be visible to unauthenticated users.  Only an authenticated user with valid RBAC permissions must be able to "unlock" locked prescriptions. They must be able to view and dispense the prescription as normal. related info: RBAC Implementation  Guidance for EPS

SCAL Requirement 1.5.4 Release a prescription for a patient or a dispensing site: Dispensers must not be able to amend prescription information after a prescription has been released from EPS.

SCAL Requirement 1.5.5 Release a prescription for a patient or a dispensing site: The dispensing system must store the prescription ID for eRD prescriptions so that dispensers can use the ID to request subsequent issues of the eRD prescription.  The dispensing system may use scheduling functionality in line with dispensing window calculations detailed below.

SCAL Requirement 1.6.1 Process released prescriptions: All prescription identifiers must be in uppercase and use hyphens as separators where necessary.

SCAL Requirement 1.6.2 Process released prescriptions: The dispensing system must display the prescription type so the dispenser can identify the type of prescriber and the relevant prescribing formulary.   The dispensing system must be capable of handling both English and Welsh Prescription Type codes.  There is no requirement for the dispensing system to validate the prescribing formulary against the prescription type. related info: Prescription Type Codes

SCAL Requirement 1.6.3 Process released prescriptions: The dispensing system must display the contact details of the prescriber and the prescribing organisation so the dispenser can contact them.

SCAL Requirement 1.6.4 Process released prescriptions: Where provided, the review date on a repeat or eRD prescription must be shown to the dispenser.  The system must alert the dispenser where the review date is within 4 weeks of the current date.

SCAL Requirement 1.6.5 Process released prescriptions: For eRD prescriptions, the dispenser must see:  â¢ the current issue â¢ the total number of authorised issues  for both the prescription and line items on the prescription.

SCAL Requirement 1.6.6 Process released prescriptions: A dispensing window must be calculated for each released item.  For acute prescriptions, repeat prescriptions, and the first issue of an eRD prescription, the dispensing window calculation is:  â¢ Window Start Date: start date of the prescription â¢ Window End Date: issue end date or item expiry date

SCAL Requirement 1.6.7 Process released prescriptions: A dispensing window must be calculated for each released item.  For subsequent issues of an eRD prescription, the dispensing window calculation is:  Window Start Date: Start Date of the prescription + ((issue N -1) x âissue durationâ) - 7 Window End Date: Issue end date or item expiry date

SCAL Requirement 1.6.8 Process released prescriptions: If the current date is outside the dispensing window, the dispenser must be alerted so they can use their clinical judgement to decide if the medication should be dispensed.

SCAL Requirement 1.6.9 Process released prescriptions: When a released prescription has an invalid signature, the dispensing system must prevent dispensing activities and mark the prescription as invalid.  The dispenser must still be able to see relevant details on the prescription, with the following being displayed as a minimum:  â¢ Details of the patient â¢ Details of the prescriber â¢ Details of the prescribing organisation

SCAL Requirement 1.7.1 Process additional instructions on released prescriptions: The dispenser must be able to see additional instructions intended for the patient on a prescription.

SCAL Requirement 1.7.2 Process additional instructions on released prescriptions: The dispenser must be able to see specific additional instructions for a prescription line item. For example, explanations about changes in dosage.

SCAL Requirement 1.7.3 Process additional instructions on released prescriptions: The dispenser must be able to see a list of current authorised repeat medication for the patient where this is provided on a prescription.   This is to support the patient in re-ordering repeat prescriptions, where relevant.  The list will include the medication's dm+d name and description. For example "Bendroflumethiazide 2.5 mg tablets."

SCAL Requirement 1.8.1 Process line items on released prescriptions: Before the point of release, a line item may be cancelled or expire.   Therefore, the status of a line item must be visible in the dispensing system after the prescription has been released.   Expired items must not be able to be dispensed to the patient.

SCAL Requirement 1.8.2 Process line items on released prescriptions: The system must use a version of the dictionary of medicines and devices (dm+d) that's as up to date as possible. It must be no more than 2 months old.   The dm+d is published every week on the Technology Reference Update Distribution (TRUD) website. related info: dm+d latest release

SCAL Requirement 1.8.3 Process line items on released prescriptions: All dm+d references must be handled without string truncation. String wrapping onto an extra line is allowed. related info: dm+d latest release

SCAL Requirement 1.8.4 Process line items on released prescriptions: The dm+d:  â¢ Virtual Medicinal Product Name (VMP) â¢ Virtual Medicinal Product Pack Description (VMPP) â¢ Actual Medicinal Product Description (AMP) â¢ Actual Medicinal Product Pack Description (AMPP)   and associated SNOMED CT codes must be used to record medication dispensed using EPS.  Descriptions must use the correct uppercase and lowercase characters as defined in dm+d. related info: dm+d latest release

SCAL Requirement 1.8.5 Process line items on released prescriptions: Mapped concepts from another terminology service to dm+d must follow the definition of âNative dm+dâ. related info: dm+d latest release

SCAL Requirement 1.8.6 Process line items on released prescriptions: Each line item will have a quantity and dm+d unit of measure.  The dispensing system must format the quantity without trailing zeros. For example, â12.5â instead of â12.50.â related info: dm+d latest release

SCAL Requirement 1.8.7 Process line items on released prescriptions: The dm+d drug name and unit of measure, or equivalent mapped concepts, must be consistently used in:     â¢ the application user interface   â¢ patient medication records  â¢ printed dispensing tokens related info: dm+d latest release

SCAL Requirement 1.8.8 Process line items on released prescriptions: The dispensing system must process dosage instructions represented as text.

SCAL Requirement 1.8.9 Process line items on released prescriptions: For schedule 2 or 3 drugs, the dispensing system must display the quantity in both words and figures with the prefix 'CD:'.   The system must process the quantity of a controlled drug based on its representation in figures, not words.

SCAL Requirement 1.8.10 Process line items on released prescriptions: Prescriber endorsements for a line item must be shown to the dispenser. related info: Requirements and Guidance for Endorsement in the Electronic Prescription Service (EPS)

SCAL Requirement 1.8.11 Process line items on released prescriptions: An expiry date must be calculated for prescribed items based on the regulations provided by the Department of Health and Social Care.  Expiry calculations operate on whole month and day boundaries. The expiry time is 23:59:59 on the last day of the expiry period. The effective date is not included in this period.  For example: A schedule 2 controlled drug prescribed (effective date) on 5th January, expires 28 days later at 23:59:59 on 2nd February. related info: The Misuse of Drugs (Amendment) (No. 2) (England, Wales and Scotland) Regulations 2015

SCAL Requirement 1.8.12 Process line items on released prescriptions: Schedule 2, 3, 4 or 5 controlled drugs and non-controlled drugs can be prescribed on the same prescription. The dispensing system must handle the different expiry periods for such medication as detailed above.

SCAL Requirement 1.8.13 Process line items on released prescriptions: The dispensing system must be able to handle unknown dm+d concepts. This could happen, for example, where a prescribing or dispensing system is out of sync with the dm+d.   Line items expressed using invalid dm+d concepts must be marked as invalid on the dispensing system.  The system must not prevent users from dispensing against an invalidated dm+d concept. related info: dm+d latest release

SCAL Requirement 1.8.14 Process line items on released prescriptions: The dispensing system must be able to handle invalid dm+d concepts for example. where an AMP has been moved from one VMP to another.  Line items expressed using an invalid dm+d concept must be marked as invalid on the dispensing system.  The system must not prevent users from dispensing an invalidated concept.

SCAL Requirement 1.9.1 Handle release rejections: When a release request is rejected, the dispenser must see an appropriate error message with the reason that the release was rejected.

SCAL Requirement 1.9.2 Handle release rejections: When a release request is rejected because the prescription has been released by another dispenser, the details of the dispensing organisation that downloaded the prescription must be displayed to the dispenser.

SCAL Requirement 2.1.1 Return a prescription to Spine: The return request must state a valid reason for why the prescription is being returned. related info: Return Reason Vocabulary

SCAL Requirement 2.1.2 Return a prescription to Spine: The return request must state the short-form prescription identifier of the prescription that is being returned.

SCAL Requirement 2.1.3 Return a prescription to Spine: The return request must state the issue number of the eRD prescription that is being returned.

SCAL Requirement 2.2.1 Send or amend a dispense notification: The dispense notification must clearly state the time the prescription was dispensed (or not dispensed) to the patient.   This time must remain consistent even where the dispense notification is amended, as this will be used to calculate the reimbursement window for the prescription in line with requirement 4.1.13.

SCAL Requirement 2.2.2a Send or amend a dispense notification: The dispense notification must state the ODS code of the reimbursement authority that the notification must be sent to.  For England, this needs to be the ODS code for the BSA (T1450).   For Wales, this needs to be the ODS code for the NWSSP (RQFZ1).

SCAL Requirement 2.2.3 Send or amend a dispense notification: When a dispense notification is submitted for an eRD prescription, the dispense notification must state:  â¢ the current issue â¢ the total number of authorised issues  for both the prescription and line items on the prescription.

SCAL Requirement 2.2.4 Send or amend a dispense notification: The dispensing system must handle item-level statuses as follows:  â¢ 0001 Item fully dispensed: A fully dispensed item  â¢ 0002 Item not dispensed: An item that cannot and will not be dispensed â¢ 0003 Item dispensed - partial: A partially dispensed item â¢ 0004 Item not dispensed - owing: An owing item â¢ 0005 Item cancelled: A cancelled item â¢ 0006 Item expired: An expired item*  *Note that the dispensing system must never set an item to expired (See SCAL 2.2.7) related info: Item Status Vocabulary

SCAL Requirement 2.2.5 Send or amend a dispense notification: The dispensing system must handle prescription-level statuses as follows:  â¢ 0003 With dispenser - active: the prescription has either partially dispensed or owing medication items â¢ 0006 Dispensed: at least 1 item on the prescription is dispensed, and the other items are either not dispensed, cancelled, or expired â¢ 0007 Not dispensed: at least 1 item on the prescription is not dispensed, and the other items are either cancelled or expired related info: Prescription Status Vocabulary

SCAL Requirement 2.2.6 Send or amend a dispense notification: A non-dispensing reason code must be provided for each item on the prescription that is not dispensed.   Where all items on the prescription are not dispensed, then a non-dispensing reason code for the prescription should also be provided. related info: Non Dispensing Reason Vocabulary

SCAL Requirement 2.2.7 Send or amend a dispense notification: Where an item on the prescription has expired, the item must be marked as "Not Dispensed" using the reason code "0008 item or prescription expired."  If all items on the prescription have expired, then the whole prescription must also be marked as "Not Dispensed" using the reason code "0008 Item or prescription expired." related info: Non Dispensing Reason Vocabulary

SCAL Requirement 2.2.8 Send or amend a dispense notification: For each dispensed medication item, the dispense notification must explicitly state:  â¢ the original prescribed item as it was released â¢ the medication dispensed

SCAL Requirement 2.2.9 Send or amend a dispense notification: The dispense notification must include dosage instructions for the dispensed medication.   These are often the same as the instructions printed on medication labels.

SCAL Requirement 2.2.10 Send or amend a dispense notification: When a dispense notification is amended, the new dispense notification must state the UUID of the dispense notification that is being amended.

SCAL Requirement 3.1.1 Withdraw a dispense notification: Dispensers must be able to withdraw the last dispense notification for a prescription.   A reason for withdrawing the notification must be provided. related info: Withdraw Reason Vocabulary

SCAL Requirement 3.1.2 Withdraw a dispense notification: The withdraw request must state the patient's NHS number.

SCAL Requirement 3.1.3 Withdraw a dispense notification: The withdraw request must state:   â¢ the short-form prescription identifier â¢ the unique ID of the dispense notification being withdrawn

SCAL Requirement 3.1.4 Withdraw a dispense notification: When a dispense notification for an eRD prescription is withdrawn, the withdraw request must state which issue of the eRD prescription the notification is being withdrawn against.

SCAL Requirement 4.1.1 Send or amend a dispense claim: A dispense claim must only be submitted when a prescription is:  â¢ 0006 Dispensed: at least 1 item on the prescription is dispensed and the other items are either not dispensed, cancelled, or expired â¢ 0007 Not dispensed: at least 1 item on the prescription is not dispensed and the other items are either cancelled or expired

SCAL Requirement 4.1.2a Send or amend a dispense claim: For suppliers creating a English Dispensing System: The dispense claim must state the ODS code of the reimbursement authority that the claim must be sent to.  For England, this needs to be the ODS code for the BSA (T1450).

SCAL Requirement 4.1.2b Send or amend a dispense claim: For suppliers creating a Welsh Dispensing System:  For Wales, this needs to be the ODS code for the NWSSP (RQFZ1).

SCAL Requirement 4.1.3 Send or amend a dispense claim: The dispense claim must state:  â¢ the overall status of the prescription â¢ the status of each line item within the prescription

SCAL Requirement 4.1.4 Send or amend a dispense claim: The system must implement the Real Time Exemption Checking (RTEC) Service to aid exemption processing. related info: RTEC Functional Requirements

SCAL Requirement 4.1.5a Send or amend a dispense claim: For suppliers creating a English Dispensing System:  Where a patient is exempt from paying prescription charges, the dispense claim must state:  â¢ the relevant prescription charge exemption code â¢ whether evidence was or was not seen to support the exemption related info: Prescription Charge Exemption Codes

SCAL Requirement 4.1.5b Send or amend a dispense claim: For suppliers creating a Welsh Dispensing System:  Welsh dispensing systems must support the following additional exemption codes:  â¢ 1001: Welsh Prescription Welsh Dispenser â No Charge  â¢ 1002: Welsh Entitlement Card

SCAL Requirement 4.1.6 Send or amend a dispense claim: To support processing exemptions, the system must calculate whether a patient is age exempt from paying prescription charges.  This calculation should be based on their date of birth.  Patients between 16 and 60 years old are not age exempt.

SCAL Requirement 4.1.7 Send or amend a dispense claim: Where a patient has paid prescription charges, the claim must state that charges have been paid.  Where the system defaults to stating that the patient has paid charges, then the dispenser should confirm that charges have indeed been paid.

SCAL Requirement 4.1.8 Send or amend a dispense claim: Where a dispense claim is submitted for an eRD prescription, it must state:  â¢ the current issue â¢ the total number of authorised issues  for both the prescription and line items on the prescription.

SCAL Requirement 4.1.9 Send or amend a dispense claim: The dispense claim must state:  â¢ each unique dm+d item dispensed to the patient â¢ the quantity of each dispensed item related info: dm+d latest release

SCAL Requirement 4.1.10a Send or amend a dispense claim: For suppliers creating a English Dispensing System: Where an item has been dispensed in a way that requires endorsements from the dispenser (for example where an item is listed on the Business Service Authority's Serious Shortage Protocol list), the dispense claim must include:  â¢ the endorsement code â¢ any additional information to support the endorsement related info: Endorsements Vocabulary

SCAL Requirement 4.1.10b Send or amend a dispense claim: For suppliers creating a Welsh Dispensing System:  Welsh dispensing systems must support the following additional endorsement codes:  â¢ WR: Waste Reduction

SCAL Requirement 4.1.11 Send or amend a dispense claim: Where an item on a prescription is not dispensed, the claim should provide a reason for each item that is not dispensed. related info: Non Dispensing Reason Vocabulary

SCAL Requirement 4.1.12 Send or amend a dispense claim: An amended claim must always reference the UUID of the previously sent claim message for a prescription.

SCAL Requirement 4.1.13 Send or amend a dispense claim: An amended claim must be received within the same reimbursement period as the original claim. The reimbursement period is defined by the effective date of the dispense notification (DN) and an original claim up to, and including, the 5th day of the following month.  For example:  A DN dated 26 September and a claim before midnight on 05 October can only be amended up to midnight on 05 October.  or  A DN dated 02 October and claim before midnight 05 November can only be amended up to midnight on 05 November.

SCAL Requirement 4.1.14 Send or amend a dispense claim: Where an amended claim changes:  â¢ the status of the prescription or an item â¢ clinical information, such as the dispensed drug and quantity  then the system must first amend the associated dispense notification before submitting the amended claim.

SCAL Requirement 4.1.15 Send or amend a dispense claim: An electronic prescription received following an emergency supply must be processed using normal dispensing and claiming processes.

SCAL Requirement 5.1.1 Print dispensing tokens for patients: The dispenser must be able to create a dispensing token to capture patient declarations or to support local repeat prescription services.   Tokens must be printed in line with the BSA's specifications for dispensing tokens. related info: Electronic Prescription Service Paper Token Specification

SCAL Requirement 5.1.2 Print dispensing tokens for patients: Printed FP10 tokens must use dm+d descriptions.

SCAL Requirement 6.1.1 Align to national data cleansing processes: The dispensing system must inform the user before Spine data cleansing takes place which could impact dispensing processes, as per 6.1.2 to 6.1.5.

SCAL Requirement 6.1.2 Align to national data cleansing processes: Dispensers have up to 180 days to submit their reimbursement claim after the date of dispensing. The date of dispensing is defined in the dispense notification where all line items are marked 'completed'. 'Completed' means all prescribed line items have a status of 'Dispensed', 'Not dispensed', 'Expired' or 'Cancelled'.  A prescription that is fully dispensed but does not have a submitted reimbursement claim will be sent to the relevant reimbursement agency without a claim block after 180 days.  A claim submission from the dispenser after this time will be rejected.

SCAL Requirement 6.1.3 Align to national data cleansing processes: A prescription with no dispensing events recorded against it will be marked as "expired" 180 days from the prescription's start date. No further dispensing activities can be carried out on this prescription.

SCAL Requirement 6.1.4 Align to national data cleansing processes: A prescription that has partially dispensed or owing items will be marked as âexpiredâ 180 days after the last dispensing event. The prescription will be sent to the relevant reimbursement agency without a claim.  Partially dispensed items will be marked as âDispensedâ.   Owing items will be marked as âNot dispensedâ.  A claim submitted after this time from the dispenser will be rejected.

SCAL Requirement 6.1.5 Align to national data cleansing processes: A prescription marked as âDispensedâ will be deleted from EPS 36 days after the electronic reimbursement or âno claim notificationâ has been sent to the reimbursement agency.  During the 36-day period, the dispensing record can still be amended to correct clinical errors provided the overall status of the prescription is not changed.

SCAL Requirement 6.2.1 Display relevant information to support dispensing activities: Users must be able to see prescriptions that do not have an endorsement and the date when the prescription is scheduled to be sent to the BSA with no associated claim. This enables users to identify and send a claim message where appropriate.

SCAL Requirement 6.2.2 Display relevant information to support dispensing activities: Users must be able to see prescriptions with outstanding items. This must include the date when EPS will mark the prescription as expired.

SCAL Requirement 6.2.3 Display relevant information to support dispensing activities: Leading up to the cut-off date for claim submissions to the BSA, users must be notified of how many unsubmitted claim messages there are for the claim month.  For example, users are notified 10, 5 and 2 working days before the 5th of the month.

SCAL Requirement 6.3.1 Batch Processing: Where a batch process is being executed for the submission of notifications or claims through the use of a refresh token, the system must ignore all backchannel logouts for the access and refresh tokens invoked for the batch process.

SCAL Requirement 6.3.2 Batch Processing: Users must be able to see prescriptions with outstanding items. This must include the date when EPS will mark the prescription as expired. While the maximum timeout period for a batch process is 12 hours, the system must terminate the batch process as soon as it is completed.

SCAL Requirement 6.3.3 Batch Processing: Where a new session is started by the same user, then the new session must not interrupt any ongoing batch processes and must be created as an entirely new session.

SCAL Requirement 7.1.1 Compatibility with 2DRx functionality in Wales: For suppliers creating a Welsh Dispensing System: Welsh dispensing systems must implement EPS functionality without detriment to existing 2DRx prescription handling.

SCAL Requirement 7.1.2 Compatibility with 2DRx functionality in Wales: For suppliers creating a Welsh Dispensing System: Welsh dispensing systems must retain barcode scanning functionality for 2DRx prescriptions
