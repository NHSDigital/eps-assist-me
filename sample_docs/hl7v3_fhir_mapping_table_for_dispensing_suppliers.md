# HL7v3 / FHIR Mapping Table for Dispensing Suppliers

## Introduction

As part of the ongoing modernisation of healthcare technology, the transition from HL7v3 to FHIR (Fast Healthcare Interoperability Resources) is a key step in improving data exchange and interoperability within the Electronic Prescription Service (EPS).

This documentation supports third-party dispensing system suppliers that are currently integrated with EPS using HL7v3 and are transitioning to FHIR via the FHIR Facade API. It gives a detailed mapping between HL7v3 fields and their corresponding FHIR elements to help suppliers validate and test their FHIR-based implementations against their existing HL7v3 systems.

The documentation covers mappings for these EPS messages and capabilities:

* releasing a prescription
* sending or amending a dispense notification
* returning a prescription
* withdrawing a dispense notification
* sending or amending a dispense reimbursement claim

This document is guidance but code itself should be considered as the source of truth.

### Releasing a prescription – Nominated Prescription Release Request

If the group-identifier parameter is missing, the request is treated as a nominated release request.

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **HL7v3 parent entity** | **HL7v3 entity** | **FHIR** | **HL7v3 cardinality** | **FHIR cardinality** | **Field description** |
| NominatedPrescriptionReleaseRequest | id | Not mapped, automatically populated. | 1..1 | n/a | The unique identifier for the release request. |
| effectiveTime | Not mapped, automatically populated. | 1..1 | n/a | The time that a release request was sent. |
| author | [Parameters](https://www.hl7.org/fhir/parameters.html).parameter.agent  [Parameters](https://www.hl7.org/fhir/parameters.html).parameter.owner | 1..1 | 1..1 | The pharmacist authoring a release request. |

### Releasing a prescription – Patient Prescription Release Request

If the group-identifier parameter is present, the request is treated as a patient release request.

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **HL7v3 parent entity** | **HL7v3 entity** | **FHIR** | **HL7v3 cardinality** | **FHIR cardinality** | **Field description** |
| PatientPrescriptionReleaseRequest | id | Not mapped, automatically populated. | 1..1 | n/a | The unique identifier for the release request. |
| effectiveTime | Not mapped, automatically populated. | 1..1 | n/a | The time that a release request was sent. |
| author | [Parameters](https://www.hl7.org/fhir/parameters.html).parameter. agent  [Parameters](https://www.hl7.org/fhir/parameters.html).parameter. owner | 1..1 | 1..1 | The pharmacist and organisation authoring the release request. |
| pertinentInformation.  pertinentPrescriptionID.  value | [Parameters](https://www.hl7.org/fhir/parameters.html). group-identifier | 1..1 | 0..1 (always present in this case) | The prescription ID of the prescription that is being released. |

### Release response

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **HL7v3 parent entity** | **HL7v3 entity** | **FHIR** | **HL7v3 cardinality** | **FHIR cardinality** | **Field description** |
| PrescriptionReleaseResponse | id | Parameters.parameter[name=passedPrescriptions].resource.identifier | 1..1 | 1..1 | The unique identifier for a release response. |
| effectiveTime | Parameters.parameter[name=passedPrescriptions].resource.identifier.meta.lastUpdated | 1..1 | 1..1 | The time that a release response was received. |
| pertinentBatchInfo.  value | Parameters.parameter[name=passedPrescriptions].resource.total | 0..\* | 1..1 | The number of prescriptions that are being released within a release response. This is not directly translated from HL7v3, it is recounted during translation. |
| component | Parameters.parameter[name=passedPrescriptions].resource.entry | 1..\* | 1..\* | Container array for the one or many prescriptions that may be released within a release response. |
| inFulfillmentOf.  priorDownloadRequestRef | Inside each Bundle (described below) mapped as:  Bundle.entry.MessageHeader.response.identifier | 1..1 | n/a | The identifier of the release request that prescriptions are being released against. |
| component | ParentPrescription | Parameters.parameter[name=passedPrescriptions].resource.entry  which will contain a  Bundle for each prescription.  All references to a Bundle below refer to this contained prescription Bundle. | 1..\* | 1..\* | Container object for the released prescription. |
| ParentPrescription | id | Bundle.identifier | 1..1 | 1..1 | The unique identifier for a prescription. |
| effectiveTime | Bundle.meta. lastUpdated | 1..1 | 1..1 | The time a prescription is valid from. |
| recordTarget.Patient | Bundle.entry. Patient | 1..1 | 1..1 | The patient a prescription is for. |
| pertinentInformation1.pertinentPrescription | Bundle (all other fields) | 1..1 | 1..1 | The content of the prescription. |
| pertinentPrescription | id | Short-Form Prescription ID  Bundle.entry.MedicationRequest.  groupIdentifier  Long-Form Prescription ID  Bundle.entry.MedicationRequest. groupIdentifier. extension:valueIdentifier | 1..1 | 1..1 | The unique identifiers for a prescription. |
| predecessor.priorPreviousIssueDate | Bundle.entry.MedicationRequest. extension:Extension-EPS-DispensingInformation. dateLastDispensed | 0..1 | 0..1 | Only for eRD prescriptions.  The date previous instance was dispensed |
| effectiveTime | Not mapped. | 1..1 | n/a | Always nullFlavour = NA |
| pertinentInformation7.pertinentReviewDate | Bundle.entry. MedicationRequest.extension: Extension-UKCore-MedicationRepeatInformation.  authorisationExpiryDate | 0..1 | 0..1 | The date a repeat prescription must be reviewed. |
| repeatNumber.low | Bundle.entry.MedicationRequest.basedOn.extension:Extension-EPS-RepeatInformation.numberOfRepeatsIssued | 0..1 | 0..1 | Always "1" at the point of issue.  For eRD prescriptions that are released, this number will  increase incrementally as the prescription is released from Spine.  Important to note that FHIR is zero-based. |
| repeatNumber.high | Bundle.entry. MedicationRequest. basedOn.extension:Extension-EPS- RepeatInformation.numberOfRepeatsAllowed | 0..1 | 0..1 | Number of authorised eRD issues for a prescription, or '1' for normal repeats.  Important to note that FHIR is zero-based. |
| component1.daysSupply  .effectiveTime.low | Bundle.entry. MedicationRequest. dispenseRequest. validityPeriod.start | 0..1 | 0..1 | The start date of an issue. |
| component1.daysSupply.effectiveTime.high | Bundle.entry. MedicationRequest. dispenseRequest. validityPeriod.end | 0..1 | 0..1 | The end date of an issue. capped at 12 months and cannot exceed the prescription's end date. Overall validity of the drug. |
| component1.daysSupply.expectedUseTime | Bundle.entry. MedicationRequest. dispenseRequest.expectedSupplyDuration | 0..1 | 0..1 | required field for eRD prescriptions to represent the expected duration of each issue expressed as a number of days, e.g. "28". |
| inFulfillmentOf.priorOriginalPrescriptionRef | Not mapped | 0..1 | n/a | The reference to an original prescription for an instance of a repeat. |
| author | Bundle.entry. MedicationRequest. requester  which will reference a:  Bundle.entry. PractitionerRole  which will reference a:  Bundle.entry. Practitioner | 1..1 | 1..1 | The person authoring and signing a prescription. |
| responsibleParty | Bundle.entry. MedicationRequest. extension:DM-ResponsiblePractitioner  which will reference a:  Bundle.entry. PractitionerRole  which will reference a:  Bundle.entry. Practitioner | 1..1 | 0..1 | The person clinically responsible for a prescription. |
| performer | Bundle.entry. MedicationRequest. performer | 0..1 | 0..1 | The ODS code of the nominated pharmacy that a prescription is going to. |
| pertinentInformation5.pertinentPrescriptionTreatmentType | Bundle.entry. MedicationRequest. courseOfTherapyType | 1..1 | 1..1 | Denotes whether a prescription is an acute, a repeat, or an eRD. |
| pertinentInformation1.pertinentDispensingSitePreference | Bundle.entry. MedicationRequest. dispenseRequest. extension:Extension-DM-PerformerSiteType | 1..1 | 1..1 | The type of nominated dispensing site a prescription is going to. |
| pertinentInformation2.pertinentLineItem | Bundle.entry. MedicationRequest | 1..4 | 1..4 | The individual line item on a prescription, limited at 4. |
| pertinentInformation4.pertinentPrescriptionType | Bundle.entry. MedicationRequest.extension: Extension-DM-PrescriptionType | 1..1 | 1..1 | The type of prescription that the BSA uses for reimbursement processing. |
| author | time | Bundle.entry. Provenance.signature.when | 1..1 | 1..1 | The time a prescription was signed. |
| agentPerson.representedOrganization | Bundle.entry. MedicationRequest. requester  which will reference a:  Bundle.entry. PractitionerRole.organization  which will reference a:  Bundle.entry. Organization | 1..1 | 1..1 | The prescribing organisation that the prescription is created in. |
| signatureText | Bundle.entry.Provenance.signature.data | 1..1 | 0..1 | The advanced electronic signature associated with a prescription. |
| pertinentLineItem | id | Bundle.entry. MedicationRequest. identifier | 1..1 | 0..1 | The unique identifier for a line item. |
| repeatNumber.low | Bundle.entry.MedicationRequest.Extension-UKCore-MedicationRepeatInformation.numberOfPrescriptionsIssued | 0..1 | 0..1 | Always '1' at the point of issue.  For eRD prescriptions that are released, this number will  increase incrementally as the prescription is released from Spine. |
| repeatNumber.high | Bundle.entry.MedicationRequest.dispenseRequest.numberOfRepeatsAllowed | 0..1 | 0..1 | The number of authorised eRD issues for a line item, or '1' for normal repeats. |
| component.lineItemQuantity | Bundle.entry. MedicationRequest. dispenseRequest. quantity | 1..1 | 1..1 | The quantity of a medication item being prescribed. |
| product.manufacturedProduct.manufacturedRequestedMaterial | Bundle.entry. MedicationRequest. medicationCodeableConcept | 1..1 | 1..1 | dm+d medication item that is being prescribed. |
| pertinentInformation1.pertinentAdditionalInstructions | Instructions intended for the patient Bundle.entry.CommunicationRequest.payload.contentString  List of repeat medications that the patient is on Bundle.entry.CommunicationRequest.payload.contentReference  which will reference a:  Bundle.entry.List  Additional instructions specific to a line item Bundle.entry.MedicationRequest.note  Controlled drug quantity in words Bundle.entry.MedicationRequest.extension:Extension-DM-ControlledDrug.quantityWords | 0..1 | 0..1 CommunicationRequests  1..\* Payload per CommunicationRequest  0..1 List | Optional instructions related to a line item. |
| pertinentInformation3.pertinentPrescriberEndorsement | Bundle.entry. MedicationRequest.extension: Extension-DM-PrescriptionEndorsement | 0..\* | 0..\* | Endorsements related to a line item, for example where the item is from the Selected List Scheme. |
| pertinentInformation2.pertinentDosageInstructions | Bundle.entry. MedicationRequest. dosageInstruction | 1..1 | 1..\* | Dosage instructions relevant to a line item. |
| inFulfillmentOf.priorOriginalItemRef | Not mapped | 0..1 | n/a | Reference to an original line item for an instance of a repeat. |

### Returning a prescription

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **HL7v3 Parent Entity** | **HL7v3 Entity** | **FHIR** | **HL7v3 Cardinality** | **FHIR Cardinality** | **Field Description** |
| DispenseProposalReturn | id | [Task.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-task?version=2.7.1-prerelease#courseOfTherapyType) identifier | 1..1 | 0..\* | The unique identifier for the return request. |
| effectiveTime | [Task.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-task?version=2.7.1-prerelease#courseOfTherapyType) authoredOn | 1..1 | 0..1 | The time the prescription is being returned to Spine. |
| author | Task.requester referencing contained PractitionerRole resource  PractitionerRole. organization referencing sibling Organization resource | 1..1 | 0..1 | The dispenser returning the prescription. |
| reversalOf.priorPrescriptionReleaseResponseRef.id | [Task.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-task?version=2.7.1-prerelease#courseOfTherapyType) focus.identifier | 0..1 | 0..1 | The release response which released the prescription that is currently being returned. |
| pertinentInformation1.pertinentPrescriptionID | [Task.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-task?version=2.7.1-prerelease#courseOfTherapyType) groupIdentifier | 1..1 | 0..1 | The prescription ID of the prescription that is being returned. |
| pertinentInformation3.pertinentReturnReason | [Task.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-task?version=2.7.1-prerelease#courseOfTherapyType) statusReason | 1..1 | 0..1 | The reason the prescription is being returned, which must be coded as per the Return Reason vocabulary. |
| pertinentInformation2.pertinentRepeatInstanceInfo | [Task.](https://simplifier.net/NHSDigital/NHSDigitalTask)extension:EPS- Repeat-Information. numberOfRepeatsIssued | 0..1 | 0..1 | The instance of the eRD prescription that is being returned.  As all eRD prescriptions have the same prescription ID, the combination of prescription ID and repeat number identifies the issue to withdraw or return. |

### Sending or amending a dispense notification

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **HL7v3 parent entity** | **HL7v3 entity** | **FHIR** | **HL7v3 cardinality** | **FHIR cardinality** | **Field description** |
| DispenseNotification | id | Bundle. identifier | 1..1 | 0..\* | The unique identifier of the dispense notification. |
| effectiveTime | [MedicationDispense](https://simplifier.net/guide/nhsdigital-medicines/Home/FHIRAssets/AllAssets/Profiles/NHSDigital-MedicationDispense?version=2.7.1-prerelease). whenHandedOver | 1..1 | 0..1 | The time at which the medication was dispensed (or not dispensed) to the patient. |
| recordTarget.patient | The sole [Patient](https://simplifier.net/guide/nhsdigital/home/fhirassets/allassets/profiles/nhsdigital-patient) resource within the Bundle or if not present MedicationDispense.subject | 1..1 | 1..1 | The patient that the medication was dispensed (or not dispensed) to. |
| primaryInformationRecipient.AgentOrg.agentOrganization | MedicationDispense.performer.actor  referencing a contained:  PractitionerRole.organization  which will reference a:  Bundle.entry. Organization.extension:Extension-ODS-OrganisationRelationships.extension:reimbursementAuthority | 1..1 | 0..\* | Used to identify the reimbursement authority that a notification needs to be sent to. Spine will have logic built around this to route the notification to the right reimbursement authority. |
| pertinentInformation2.pertinentCareRecordElementCategory.component.actRef | MedicationDispense.identifier | 1..1 | 0..\* | A legacy field that was created to support structured shared care records and SCRa. |
| replacementOf | MessageHeader.extension:Extension-replacementOf | 0..1 | 0..1 | A reference to the previous dispense notification, where an amended dispense notification is being sent. |
| sequelTo.priorPrescriptionReleaseEventRef | MessageHeader. response | 1..1 | 0..1 | A reference to the release response that released the prescription being dispensed. |
| pertinentInformation1.pertinentSupplyHeader | MedicationDispense | 1..1 | 1..\* | An entity representing the original prescription in the context of a dispense notification. |
| pertinentSupplyHeader | id | Bundle. identifier | 1..1 | 1..1 | The unique identifier for the SupplyHeader. |
| effectiveTime | Not mapped. | 1..1 | N/A | Fixed value in the output HL7v3 of "<effectiveTime nullFlavor="NA"/>" |
| repeatNumber.low | [MedicationDispense](https://simplifier.net/guide/nhsdigital-medicines/Home/FHIRAssets/AllAssets/Profiles/NHSDigital-MedicationDispense).authorizingPrescription  referencing a contained  MedicationRequest.basedOn.extension: Extension-EPS-RepeatInformation. numberOfRepeatsIssued | 0..1 | 0..1 | An entity that identifies the instance of a repeat prescription that is being dispensed. |
| repeatNumber.high | [MedicationDispense](https://simplifier.net/guide/nhsdigital-medicines/Home/FHIRAssets/AllAssets/Profiles/NHSDigital-MedicationDispense).authorizingPrescription  referencing a contained  MedicationRequest.basedOn.extension:  Extension-EPS-RepeatInformation. numberOfRepeatsAllowed | 0..1 | 0..1 | An entity that identifies the number of authorised repeats for a prescription. |
| author | MedicationDispense.performer.actor  referencing a contained:  PractitionerRole | 1..1 | 1..1 | An entity used to identify the dispenser dispensing a prescription. |
| pertinentInformation2.pertinentNonDispensingReason | MedicationDispense.extension: Extension-DM-PrescriptionNonDispensingReason | 0..1 | 0..1 | The reason a prescription was not dispensed, if it was not dispensed. |
| pertinentInformation3.pertinentPrescriptionStatus | [MedicationDispense.](https://simplifier.net/packages/uk.nhsdigital.r4.test/2.7.1-prerelease/files/717006) extension:Extension-EPS-TaskBusinessStatus | 1..1 | 1..1 | The intended status of the prescription as a result of the dispense notification. |
| pertinentInformation4.pertinentPrescriptionID | [MedicationDispense](https://simplifier.net/guide/nhsdigital-medicines/Home/FHIRAssets/AllAssets/Profiles/NHSDigital-MedicationDispense).authorisingPrescription  referencing a contained  MedicationRequest.groupidentifier | 1..1 | 1..1 | The short form identifier of the prescription that is being dispensed. |
| inFulfillmentOf.priorOriginalPrescriptionRef | [MedicationDispense](https://simplifier.net/guide/nhsdigital-medicines/Home/FHIRAssets/AllAssets/Profiles/NHSDigital-MedicationDispense). authorisingPrescription  referencing a contained  MedicationRequest.  groupidentifier.extension: Extension-DM-PrescriptionId | 1..1 | 1..\* | The long-form identifier of the prescription being dispensed. |
| predecessor.priorSupplyHeaderRef | Not mapped | 0..1 | N/A | A reference to a previous SupplyHeader where the dispense notification is a partial dispense and therefore must reference a previous dispense notification. |
| pertinentInformation1.pertinentSuppliedLineItem | [MedicationDispense](https://simplifier.net/guide/nhsdigital-medicines/Home/FHIRAssets/AllAssets/Profiles/NHSDigital-MedicationDispense) | 1..4 | 1..\* | An entity representing the line items on a prescription in the context of a dispense notification. |
| author | time | (The time on our servers we receive the dispense notification bundle) | 1..1 | N/A | The time that the dispense notification message was sent.  This is the time that the medication was dispensed (or not dispensed) to the patient. |
| AgentPerson | MedicationDispense.performer.actor  referencing a contained:  PractitionerRole | 1..1 | 1..\* | The dispensing practitioner and organisation that sent the dispense notification. |
| pertinentSuppliedLineItem | id | MedicationDispense. identifier | 1..1 | 0..1 | The unique identifier for the supplied line item. |
| effectiveTime | Not mapped. | 1..1 | 1..1 | Fixed value that should default to "<effectiveTime nullFlavor="NA"/> |
| repeatNumber.low | MedicationDispense.authorisingPrescription  referencing a contained  MedicationRequest.extension: Extension-UKCore-MedicationRepeatInformation. numberOfPrescriptionsIssued | 0..1 | 0..1 | An entity that identifies the instance of a line item that is being dispensed. |
| repeatNumber.high | MedicationDispense.authorisingPrescription  referencing a contained  MedicationRequest. dispenseRequest. numberOfRepeatsAllowed | 0..1 | 0..1 | An entity that identifies the number of authorised repeats for a line item. |
| consumable.requestedManufacturedProduct. manufacturedRequestedMaterial | MedicationDispense.authorisingPrescription  referencing a contained  MedicationRequest. medicationCodeableConcept | 1..1 | 1..\* | The original drug prescribed to the patient, expressed as a VMP or AMP description concept. |
| component1.supplyRequest | MedicationDispense.authorisingPrescription  referencing a contained  MedicationRequest. dispenseRequest.quantity | 1..1 | 1..\* | The quantity of the drug prescribed to the patient. |
| pertinentInformation1.pertinentRunningTotal | Not mapped | 0..1 | N/A | An entity that enables the tracking of the quantity of a drug supplied across a series of dispense events. |
| pertinentInformation2.pertinentNonDispensingReason | [MedicationDispense.](https://simplifier.net/packages/uk.nhsdigital.r4.test/2.7.1-prerelease/files/717006) statusReasonCodeableConcept | 0..1 | 0..1 | The reason a medication was not dispensed, if it was not dispensed. |
| pertinentInformation3.pertinentItemStatus | [MedicationDispense.](https://simplifier.net/packages/uk.nhsdigital.r4.test/2.7.1-prerelease/files/717006) type.coding | 1..1 | 0..\* | The intended status of the line item as a result of the dispense notification. |
| inFulfillmentOf.priorOriginalItemRef | MedicationDispense.authorisingPrescription. MedicationRequest. identifier | 1..1 | 1..\* | The unique identifier of the line item that is being dispensed. |
| predecessor.priorSuppliedLineItemRef | Not mapped | 0..1 | N/A | A reference to a previous supplied line item where the dispense notification is a partial dispense and therefore must reference a previous dispense notification. |
| component.suppliedLineItemQuantity | MedicationDispense.quantity, MedicationDispense.medicationCodeableConcept, MedicationDispense.dosageInstruction | 1..\* | 1..1 | The actual drug dispensed to the patient, which is expressed as an AMPP concept.  This is distinct to the supplied line item, which will generally be expressed as a generic VMP concept. |
| suppliedLineItemQuantity | pertinentInformation1.pertinentSupplyInstructions | [MedicationDispense.](https://simplifier.net/packages/uk.nhsdigital.r4.test/2.7.1-prerelease/files/717006) dosageinstruction | 1..\* | 0..\* | Instructions about how the drug should be administered, given by the dispenser.  These are often in addition to the dosage instructions on the original prescription.  For example, the dispenser may provide crucial information about drug interactions within the supply instructions, for example 'do not consume alcohol when taking this <AMPP concept> medication'. |
| pertinentInformation1.pertinentAdditionalInstructions | Not mapped. | 0..1 | N/A | Optional additional instructions that the dispenser might give about a drug being dispensed.  Crucially, these are distinct to the additional instructions provided by the prescriber on a prescription. |
| product.suppliedManufacturedProduct | MedicationDispense.  medicationCodeableConcept | 1..1 | 1..1 | The actual drug dispensed to the patient, which is expressed as an AMPP concept.  This is distinct to the supplied line item, which will generally be expressed as a generic VMP concept. |
| quantity | MedicationDispense.quantity | 1..1 | 1..1 | The actual quantity supplied to the patient. This could be different to the quantity prescribed. |

### Withdrawing a dispense notification

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **HL7v3 parent entity** | **HL7v3 entity** | **FHIR** | **HL7v3 cardinality** | **FHIR cardinality** | **Field description** |
| ETPWithdraw | id | Task.identifier | 1..1 | 0..\* | The unique identifier for the withdraw request. |
| effectiveTime | Task.authoredOn | 1..1 | 0..1 | The time the dispense notification was withdrawn. |
| author.AgentPersonSDS. agentPersonSDS.id | Task.requester  referencing a contained  PractitionerRole.practioner.identifier | 1..1 | 0..1 | The identifier for the healthcare professional who has requested the dispense notification withdrawal. |
| author.AgentPersonSDS.id | Task.requester  referencing a contained  PractitionerRole.identifier | 1..1 | 0..1 | The identifier for role profile of the healthcare professional who has requested the dispense notification withdrawal. |
| recordTarget.patient.id | Task.for.identifier | 1..1 | 1..1 | The 10 digit NHS number for the patient that the medication was dispensed (or not dispensed). |
| pertinentInformation3.pertinentWithdrawID.value | Task.groupidentifier | 1..1 | 0..1 | The value that relates to original prescription. |
| pertinentInformation1.pertinentRepeatInstanceInfo.value | Task.extension:Extension-EPS-RepeatInformation .extension:numberOfRepeatsIssued | 0..1 | 0..1 | The value that relates to one of the instances of a repeat prescription. |
| pertinentInformation2.pertinentWithdrawType.value | (hard coded to the value 'LD') | 1..1 | n/a | The value that relates to the dispensing event to be withdrawn. 'LD' means the last dispensing event. |
| pertinentInformation5.pertinentWithdrawReason.value | Task.statusReason | 1..1 | 0..1 | The list of reasons why a dispense notification is being withdrawn. |
| pertinentInformation4.pertinentDispenseNotificationRef.id | Task.focus.identifier | 0..\* | 0..1 | The identifier of the original dispense notification, if one exists. |

### Sending or amending a dispense reimbursement claim

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **HL7v3 parent entity** | **HL7v3 entity** | **FHIR** | **HL7v3 cardinality** | **FHIR cardinality** | **Field description** |
| DispenseClaim | id | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) identifier | 1..1 | 1..\* | The unique identifier for the dispense claim. |
| effectiveTime | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) created | 1..1 | 1..1 | The date and time that the dispense claim message was submitted. |
| primaryInformationRecipient.AgentOrg.agentOrganization | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease)insurance.coverage | 1..1 | 1..1 | Used to identify the reimbursement authority that a claim needs to be sent to. Spine will have logic built around this to route the claim to the right reimbursement authority. |
| replacementOf.priorMessageRef | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) extension: Extension-replacementOf | 0..1 | 0..1 | Reference to the previous dispense claim in the act of sending a claim amend. |
| coverage.coveringChargeExempt | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease)item. programCode. coding: prescription-charge-exemption | 0..1 | 1..1 | Whether a patient is exempt from paying prescription charges for a given prescription and why. |
| sequelTo.priorPrescriptionReleaseEventRef | Not mapped | 1..1 | N/A | A link to the prescription release event that released the prescription that is being dispensed. |
| coverage.coveringChargeExempt | authorization.authorizingEvidenceSeen | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease)item. programCode. coding: DM-exemption-evidence | 0..1 | 0..1 | Confirmation from the dispenser on whether they have seen evidence to qualify a patient's exemption status. |
| pertinentInformation1.pertinentSupplyHeader | id | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) identifier | 1..1 | 1..1 | The unique identifier for the SupplyHeader entity. |
| repeatNumber.low | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease)item.detail. extension: Extension-EPS-RepeatInformation.extension: numberofRepeatsIssued | 0..1 | 0..1 | An entity that identifies the instance of a  prescription that is being claimed for. |
| repeatNumber.high | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease)item.detail. extension: Extension-EPS-RepeatInformation.extension: numberofRepeatsAllowed | 0..1 | 0..1 | An entity that identifies the number of authorised repeats for a line item. |
| pertinentInformation3.pertinentPrescriptionStatus | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) item.extension: Extension-EPS-TaskBusinessStatus | 1..1 | 1..1 | The status of the prescription when the claim is submitted. |
| pertinentInformation4.pertinentPrescriptionID | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) prescription.extension: Extension-DM-GroupIdentifier.extension: shortForm | 1..1 | 1..1 | The short-form prescription ID of the prescription being dispensed. |
| inFulfillmentOf.priorOriginalPrescriptionRef | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) prescription.extension: Extension-DM-GroupIdentifier.extension: UUID | 1..1 | 1..1 | The long-form prescription ID of the prescription being dispensed. |
| predecessor.priorSupplyHeaderRef | Not mapped. | 0..1 | N/A | Reference to a previous SupplyHeader if the prescription was fulfilled through a series of partial dispense events. |
| pertinentInformation2.pertinentNonDispensingReason | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) item.extension: Extension-EPS-TaskBusinessStatusReason | 0..1 | 0..1 | The reasons why a prescription was not dispensed. |
| legalAuthenticator | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease)provider  referencing a contained  PractitionerRole | 1..1 | 1..1 | The details of the dispenser who submitted the claim. |
| pertinentInformation1.pertinentSuppliedLineItem | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) item.detail | 1..\* | 1..\* | An entity representing the line items on a prescription in the context of a dispense notification. |
| legalAuthenticator | time | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) created | 1..1 | 1..1 | The date and time when the dispense claim was originally submitted.  Where the claim is an amended claim, this will be distinct to the date and timestamp of the claim message.  Otherwise, this will be the same as the date and timestamp of the claim message. |
| pertinentInformation1.pertinentSuppliedLineItem | id | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) item.detail. extension: Extension-ClaimSequenceIdentifier | 1..1 | 1..1 | The unique identifier for the supplied line item. |
| repeatNumber.low | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease)item.detail.subDetail. extension: Extension-EPS-RepeatInformation. numberofRepeatsIssued | 0..1 | 0..1 | An entity that identifies the instance of a repeat item that is being claimed for. |
| repeatNumber.high | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease)item.detail.subDetail. extension: Extension-EPS-RepeatInformation. numberofRepeatsAllowed | 0..1 | 0..1 | An entity that identifies the number of authorised repeats. |
| pertinentInformation3.pertinentItemStatus | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) item.detail. modifier | 1..1 | 1..\* | The status of the line item when the claim is submitted. |
| inFulfillmentOf.priorOriginalItemRef | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) item.detail. extension: Extension-ClaimMedicationRequestReference | 1..1 | 1..1 | References the line item identifier of the line item on the original prescription. |
| predecessor.priorSuppliedLineItemRef | Not mapped | 0..1 | N/A | Reference to a previous supplied line item if the prescription was fulfilled through a series of partial dispense events. |
| pertinentInformation2.pertinentNonDispensingReason | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) item.detail.extension: Extension-EPS-TaskBusinessStatusReason | 0..1 | 0..1 | Reasons why a medication item was not dispensed. |
| component.suppliedLineItemQuantity | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) item.detail. subDetail | 0..\* | 0..\* | The set of drugs supplied in fulfilment of this line item. |
| pertinentInformation1.pertinentRunningTotal | Not mapped | 0..1 | N/A | An entity that enables the tracking of the quantity of a drug supplied across a series of dispense events. |
| component.suppliedLineItemQuantity | product.suppliedManufacturedProduct. manufacturedSuppliedMaterial | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) item.detail.subDetail. productOrService | 1..1 | 1..1 | The actual drug dispensed to the patient, which is expressed as an AMPP concept. |
| quantity | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) item.detail.subDetail. quantity | 1..1 | 1..1 | The quantity of the drug dispensed to the patient. |
| pertinentInformation2.pertinentDispensingEndorsement | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) item.detail. programCode.coding: medicationdispense-endorsement | 1..\* | 0..\* | Endorsements added to line items enable dispensers to get reliably compensated for the services they provide. |
| pertinentInformation1.pertinentChargePayment | [Claim.](https://simplifier.net/guide/nhsdigital-medicines/home/fhirassets/allassets/profiles/nhsdigital-claim?version=2.7.1-prerelease) item.detail. programCode.coding: DM-prescription-charge | 1..1 | 0..\* | An entity identifying whether the patient paid for their prescription. |
