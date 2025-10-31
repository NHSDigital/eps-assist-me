# Reference guide - NHS England Digital

---

## Deprecation and retirement policy

### APIs

In order to keep our API and service estate manageable, we might [deprecate](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#api-status) and eventually [retire](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#api-status) an API if:

- we have built a new major version of the API
- we have built a new API that provides equivalent capabilities - such as a FHIR API
- the API is not fit for purpose, for example because it doesn't include important use cases
- the API is not being used or has limited usage
- the API is insecure or a security risk

We appreciate that this might cause inconvenience, but we must use public funds efficiently and cannot afford to maintain replaced or obsolete APIs indefinitely.

If we deprecate an API:

- we will let you know
- the API will still be available for use
- our service levels will still apply
- we are unlikely to make any updates
- we will not permit new integrations - with the exception of in-flight integrations
- we will consult with you on an appropriate date to retire the API
- if the API is being replaced, we will create a migration guide to help you integrate with the replacement API

For details on APIs that are currently being considered for deprecation or retirement, see our [interactive product backlog](https://nhs-digital-api-management.featureupvote.com/?order=popular&filter=allexceptdone&tag=deprecation-retirement&deleted=0#controls).

### Standards

In order to keep our API standards estate manageable, we might [deprecate](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#api-status) and eventually [retire](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#api-status) an API standard if:

- the standard is no longer is use
- the standard is in use but is no longer strategic
- the standard has been replaced by a newer standard

If we deprecate an API standard:

- we will tag the standard as deprecated in the [NHS Data Standards Directory](https://data.standards.nhs.uk/)
- we will announce the deprecation to everyone with a [developer account](https://identity.prod.api.platform.nhs.uk/auth/realms/developer-identity/protocol/openid-connect/auth?client_id=digital-onboarding-service&redirect_uri=https%3A%2F%2Fonboarding.prod.api.platform.nhs.uk%2Fsignin-oidc&response_type=code&scope=openid%20profile&code_challenge=svumNXTwncmUyJbmNEylhioQoBW2IhUOarXwTUpfjME&code_challenge_method=S256&response_mode=form_post&nonce=638085268455647979.MzgzYzI2NDktN2UwNy00MDk3LWE1NzYtNDBjNmQyM2IxMGEyZjhmMWNmMTgtNWVhNS00ZDcyLWEzMzgtMTQxNmZkMTM0NDIz&state=CfDJ8IEvpKdkC89JpoZmfPIhl8huH2sWymURF9oWI6dbgRxPLf2bwKKtIMMy8fhvo6AuJvBU2h8kS4DrxOC6LKPp4B4eN3QFjmTbM24_tfzdJJFvy9Ywl5Wcoq3l8NrX5ONhj7V6VISfWPI3Lnx0LGvKJg078JHx6e6Sh8J5T2pVwg3WHZ162bN9IPFJfPLW_WgoywP-tXWJWrVTUuR10lRKP5EHZCDGGBlIV2u0LX5eWtKAH2brNh_widPRZjmq-jGUrgDmfTAzhM31qWkLell0vofyZx5qpZpw0kqE8hfHrLEOguuRGjFqR9AfnqKjIQWGXJddNN59vB6s28izlN32FMpB9VJCPbw0juC9f7TWpioI12zjpy32PLmBONacVE97VId8Mx6S1tq8IxF3O50Dn1yf5f_Q69Rrgwf5DPgdRHVROohQhTD6eN2p1NJ7r4bWWjPoGE2MwVPN1TZJTUZkUesByAB-JARzUnlsQleDSWs8&x-client-SKU=ID_NETSTANDARD2_0&x-client-ver=6.10.0.0)
- we will set a retirement date as 12 months from the date of deprecation
- the API standard will still be available for use

If we retire an API standard:

- we will tag the standard as retired in the [NHS Data Standards Directory](https://data.standards.nhs.uk/)
- we will announce the retirement to everyone with a [developer account](https://identity.prod.api.platform.nhs.uk/auth/realms/developer-identity/protocol/openid-connect/auth?client_id=digital-onboarding-service&redirect_uri=https%3A%2F%2Fonboarding.prod.api.platform.nhs.uk%2Fsignin-oidc&response_type=code&scope=openid%20profile&code_challenge=svumNXTwncmUyJbmNEylhioQoBW2IhUOarXwTUpfjME&code_challenge_method=S256&response_mode=form_post&nonce=638085268455647979.MzgzYzI2NDktN2UwNy00MDk3LWE1NzYtNDBjNmQyM2IxMGEyZjhmMWNmMTgtNWVhNS00ZDcyLWEzMzgtMTQxNmZkMTM0NDIz&state=CfDJ8IEvpKdkC89JpoZmfPIhl8huH2sWymURF9oWI6dbgRxPLf2bwKKtIMMy8fhvo6AuJvBU2h8kS4DrxOC6LKPp4B4eN3QFjmTbM24_tfzdJJFvy9Ywl5Wcoq3l8NrX5ONhj7V6VISfWPI3Lnx0LGvKJg078JHx6e6Sh8J5T2pVwg3WHZ162bN9IPFJfPLW_WgoywP-tXWJWrVTUuR10lRKP5EHZCDGGBlIV2u0LX5eWtKAH2brNh_widPRZjmq-jGUrgDmfTAzhM31qWkLell0vofyZx5qpZpw0kqE8hfHrLEOguuRGjFqR9AfnqKjIQWGXJddNN59vB6s28izlN32FMpB9VJCPbw0juC9f7TWpioI12zjpy32PLmBONacVE97VId8Mx6S1tq8IxF3O50Dn1yf5f_Q69Rrgwf5DPgdRHVROohQhTD6eN2p1NJ7r4bWWjPoGE2MwVPN1TZJTUZkUesByAB-JARzUnlsQleDSWs8&x-client-SKU=ID_NETSTANDARD2_0&x-client-ver=6.10.0.0)
- we will archive the standard
- we will discourage from further use

For details on API standards that are currently being considered for deprecation or retirement, see our [interactive product backlog](https://nhs-digital-api-management.featureupvote.com/?order=popular&filter=allexceptdone&tag=deprecation-retirement&deleted=0#controls).

---

## Error handling

Our APIs are designed to be highly available and robust, but you should write your software to deal with common temporary problems that happen with all types of APIs:

- unreliable network connectivity - particularly on mobile devices
- rate limiting
- temporary service problems

Your API-calling application should have a mechanism to automatically try again, possibly giving status information to your end user, before giving up. If your application fails on the first API failure, it could be quite brittle.

There are more and more client libraries that support this type of robustness, but, more than likely, you'll need to write your own code. If you do, consider making it part of a standard REST API calling library.

Your application should:

- examine the return status code
- decide on a pattern for trying again
- incorporate wait or loop code that delays for x milliseconds before trying again

Think carefully about how to handle this as retrying immediately could make the problem worse. Some examples of retry strategies are to use:

- [exponential backoff](https://gbr01.safelinks.protection.outlook.com/?url=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FExponential_backoff&data=05%7C01%7Cmatthew.firth1%40nhs.net%7Cf129fee301f34bcaca4908db44dc8df4%7C37c354b285b047f5b22207b48d774ee3%7C0%7C0%7C638179486275128817%7CUnknown%7CTWFpbGZsb3d8eyJWIjoiMC4wLjAwMDAiLCJQIjoiV2luMzIiLCJBTiI6Ik1haWwiLCJXVCI6Mn0%3D%7C3000%7C%7C%7C&sdata=ark1NtepsH0%2BTTZqyyfMYKF%2BfIt1AQkkAhjqF9xXDVc%3D&reserved=0)
- overnight processing  - this works well with longer retry intervals, such as doubling of the interval, that is, 1 second, 2 seconds, 4 seconds, and so on.
- if an end user is present, a lower initial retry interval, such as 200ms with a maximum retry interval of 3 seconds

### Handling rate limit error code 429

See [rate limits](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#rate-limits).

### Retries in timeout or error situations

Your application should not assume that when a timeout or error occurs, it is an irrecoverable error - it should automatically retry.

For end user interactions, keeping your timeouts lower than 30 seconds (often the default timeout) helps with the responsiveness of your application. You might want to display a message to the end user that, “Connections are taking longer than normal…”.

5xx status codes can easily be transient problems, and as they are server side your application cannot do anything about them directly. This means you do not need to analyse the response. It is worth noting that some of our APIs provide a Retry-After header for 503 responses, which:

- gives you the number of seconds to wait before trying again, optimised for the specific API
- might contain a date-time, indicating that the service is down for maintenance, and when it will be available. For more details, see the [HTTP-Date in RFC9110 for a definition](https://gbr01.safelinks.protection.outlook.com/?url=https%3A%2F%2Fwww.rfc-editor.org%2Frfc%2Frfc9110.html%23http.date&data=05%7C01%7Cmatthew.firth1%40nhs.net%7Cf129fee301f34bcaca4908db44dc8df4%7C37c354b285b047f5b22207b48d774ee3%7C0%7C0%7C638179486275128817%7CUnknown%7CTWFpbGZsb3d8eyJWIjoiMC4wLjAwMDAiLCJQIjoiV2luMzIiLCJBTiI6Ik1haWwiLCJXVCI6Mn0%3D%7C3000%7C%7C%7C&sdata=415wYLvP00ivRtX8BJqubOLv2ZT%2FfsgA4IRQ3xudfFg%3D&reserved=0)

Whether you process this header or not, consider logging the values for analysis and using them to improve the next version of your software.

Although code 429 applies to rate limiting, consider retrying all 4xx status codes automatically.

### Retries when updating data

If you are creating, updating or deleting data, the situation is more complex. We recommend to our API producers to expect a full retry, that is, to receive the entire request again including headers.

The API specification should specify any special behaviours to expect, for instance, Spine APIs tend to use a unique messageID to de-duplicate the requests.

### Maximum polling attempts

Do not let your application keep retrying an API forever, but configure it to give up at an appropriate time. For any guidance on the maximum number of retries, see its API specification.

If there is no advice, select something that is a good balance for your situation. Where your application has end users, consider a much lower limit. For example, if your application has paused for as long as 10 seconds, many end users will have tried to refresh the page and start again.

---

---

## HTTP status codes

We use standard HTTP status codes to show whether an API request succeeded or not. They are usually in the range:

- 200 to 299 if it succeeded, including code 202 if it was accepted by an API that needs to wait for further action
- 400 to 499 if it failed because of a client error by your application
- 500 to 599 if it failed because of an error on our server

For details of 2xx and 4xx responses for a specific API, see its API specification.

We do not list specific 5xx responses in API specifications - rather, you should code your application to handle all 5xx responses equally.

For more details on handling error codes, see [error handling](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#error-handling).

### 4xx status codes

A 4xx status code means there was a problem with the client request to the API. The most common error codes and their meanings are as follows:

- HTTP code: 400
  - Error message: INVALID_VALUE
  - Meaning: Required header parameter is not valid, for example, the access token is invalid. Ensure the header parameter is valid and conforms to your API's endpoint specification.
- HTTP code: 400
  - Error message: MISSING_VALUE
  - Meaning: Required header parameter is missing, for example, the access token is missing. Ensure the header parameter is populated and conforms to your API's endpoint specification.
- HTTP code: 401
  - Error message: ACCESS_DENIED
  - Meaning: Authorisation credentials are not valid. Make sure you follow the instructions in the appropriate security pattern for your API's access mode.
- HTTP code: 401
  - Error message: UNAUTHORISED
  - Meaning: Authorisation credentials are missing. Make sure you follow the instructions in the appropriate security pattern for your API's access mode.
- HTTP code: 403
  - Error message: ACCESS_DENIED
  - Meaning: Authorisation credentials do not have permissions to perform the request. Make sure you follow the instructions in the appropriate security pattern for your API's access mode.
- HTTP code: 403
  - Error message: FORBIDDEN
  - Meaning: The user is not permitted to perform an action. Make sure you follow the instructions in the appropriate security pattern for your API's access mode.
- HTTP code: 404
  - Error message: RESOURCE_NOT_FOUND
  - Meaning: No dataset resources were found.
- HTTP code: 429
  - Error message: TOO_MANY_REQUESTS
  - Meaning: You have exceeded your application's rate limit.

### 5xx status codes

A 5xx status code means there was a problem with the server responding to the API request. The most common error codes and their meanings are as follows:

- HTTP code: 500
  - Error message: INTERNAL_SERVER_ERROR
  - Meaning: The server does not know how to handle the request.
- HTTP code: 501
  - Error message: NOT_IMPLEMENTED
  - Meaning: The server does not support the request method, which it cannot handle. (The only methods that servers are required to support are GET and HEAD.)
- HTTP code: 502
  - Error message: BAD_GATEWAY
  - Meaning: The server got an invalid response, while working as a gateway or proxy to another server.
- HTTP code: 503
  - Error message: SERVICE_UNAVAILABLE
  - Meaning: The server cannot handle the request because it is down for maintenance or overloaded.
- HTTP code: 504
  - Error message: GATEWAY_TIMEOUT
  - Meaning: The server did not get a response in time, while working as a gateway or proxy to another server.

---

## Non-NHS England APIs

Our [API and integration catalogue](https://digital.nhs.uk/developer/api-catalogue) contains some APIs not owned by us at NHS England but by associated organisations. These include other parts of the NHS and various partner organisations. Use the API and integration catalogue 'owner' filter to see these APIs.

---

## Open source

### Coding in the open

As per the [NHS service standard](https://service-manual.nhs.uk/standards-and-technology/service-standard), we aim to [make new source code open](https://service-manual.nhs.uk/standards-and-technology/service-standard-points/12-make-new-source-code-open).

The source code for many of our newer APIs is available for inspection, re-use and contribution in our [public repository](https://github.com/NHSDigital) on Github.

In some cases there might be more than one repository, or 'repo', for a single API. For example, there might be:

- one repo for the API layer - proxy, sandbox and specification
- a separate repo for the back-end service - business logic and data persistence

Sometimes the API repo is in the open but the back-end service repo is not.

To find the repos for a specific API, look for an 'Open source' section in the API specification in our [API and integration catalogue](https://digital.nhs.uk/developer/api-catalogue). Alternatively, just search for the API name directly in GitHub.

In general, we welcome contributions. Instructions for contributing to a specific API are in the CONTRIBUTING.md file in the repo. If you are thinking of contributing a significant change, not just a bug fix, you might want to [contact us](https://digital.nhs.uk/developer/help-and-support) to discuss it first.

### API client code

Integrating with APIs is easier when you have API client code to copy or re-use. This might be a pre-built API client library or just some sample API client code to copy and re-use.

We don't have much open source API client code, but where we do, it is listed in the 'Open source' section in the API specification in our [API and integration catalogue](https://digital.nhs.uk/developer/api-catalogue).

We would like to have more API client code. Some of our teams have plans for this, so more might appear over time. But we're also open to publishing links to community-built API client code.

So, if you have any open source code that you'd be willing to share, [contact us](https://digital.nhs.uk/developer/help-and-support) with the details and we'll look into publishing a link to it.

### Utilities and libraries

Here's a list of open source utilities and libraries that might be useful for people building healthcare software. We provide these on an 'as is' basis - we have not tested any of them nor do we specifically endorse their use.

- Resource: Firely .NET SDK
  - Description: .NET / C# library for building or consuming FHIR APIs.
  - Links: GitHub repo
- Resource: HAPI FHIR
  - Description: Java library for building or consuming FHIR APIs.
  - Links: GitHub repo
- Resource: SMART on FHIR JavaScript library
  - Description: JavaScript library for connecting SMART apps to FHIR servers.
  - Links: GitHub repo
- Resource: SMART FHIR Client
  - Description: Python client for FHIR servers supporting the SMART on FHIR protocol.
  - Links: GitHub repo
- Resource: nhs-number
  - Description: Python package containing utilities for NHS numbers including validity checks, normalisation and generation.
  - Links: GitHub repo | Python Package index | Docs
- Resource: NHSnames
  - Description: Utility to decapitalise NHS organisation names as retrieved from ODS
  - Links: GitLab repo | Docs

---

## Performance testing

We do not currently have an environment you can use for performance testing your integration.

If you need to performance test your integration, we recommend you build stubs to simulate our APIs.

If you think it would make integration easier if we provided a performance test environment, you can can upvote the [feature suggestion on our interactive product backlog](https://nhs-digital-api-management.featureupvote.com/suggestions/151048/performance-testing-capability).

See also [response times](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#response-times).

---

## Rate limits

For some of our APIs, we limit the number of transactions you can make per unit of time. This protects our service against excessive use and denial-of-service (DoS) attacks, and is also to encourage you to use our APIs efficiently.

Our default rate limit for the production environment is 5 transactions per second (tps) per application per API, which should be enough for low volume use cases. Our back-end systems can generally handle much higher loads, so if you need a higher rate limit, [contact us](https://digital.nhs.uk/developer/help-and-support). You will need to demonstrate you are using the API efficiently.

Note that rate limits:

- are applied per minute, not per individual second - so at the default limit of 5tps, you can perform up to 300 transactions in any given (rolling) minute
- apply per application, per API
- only apply to APIs on our API platform - where the domain is https://api.service.nhs.uk
- do apply to our OAuth 2.0 authorisation service - https://api.service.nhs.uk/oauth

If you go over your application's rate limit you'll receive a response with an HTTP status of 429 (Too Many Requests).

Some of our APIs also have global rate limits for additional protection. These should not normally affect you, but in extreme cases you might get a 429 response even if you have not gone over your application's rate limit.

Our path-to-live environments have very low default rate limits. They are for functional testing only - you should not use them for [performance testing](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#performance-testing).

For more information on strategies for handling error codes, see [error handling](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#error-handling).

---

## Response times

We do not have formal service level agreements (SLAs) for API response times.

That said, we do monitor response times and react where we believe them to be unreasonable.

As a general guide, you can assume that all our APIs respond in under 0.5 seconds for 95% of the time, unless otherwise stated in the API documentation. In other words they are 'fast enough' for a standard use case where an end user is present. Most of our APIs are much, much faster than that.

This applies to the production environment only - response times might be different (faster or slower) in test environments.

If you want to discuss response times for a particular use case - for example if you need to make multiple API calls and want to be sure the end-to-end response time will be acceptable, [contact us](https://digital.nhs.uk/developer/help-and-support).

---

## Service levels

Each of our APIs has a service level which defines how available it is and how quickly we fix issues.

The service level does not cover [API response times](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#response-times).

The service level applies to the production environment only, not to our test environments. APIs with an [API status](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#api-status) of alpha or retired are not available in production and thus do not have a service level defined.

Whilst we expect to meet these service levels, they are not guaranteed, and we will not be liable to you if we do not meet them.

The service levels are as follows:

- Characteristic: Operational hours
  - Bronze: 8am to 6pm, Monday to Friday excluding bank holidays (expected minimum, with many APIs available outside business hours)
  - Silver / Silver Plus\* : 24 hours a day, 365 days a year
  - Gold: 24 hours a day, 365 days a year
  - Platinum / Platinum Plus: 24 hours a day, 365 days a year
- Characteristic: Supported hours
  - Bronze: 8am to 6pm, Monday to Friday excluding bank holidays
  - Silver / Silver Plus\* : 8am to 6pm, Monday to Friday excluding bank holidays
  - Gold: 24 hours a day, 365 days a year
  - Platinum / Platinum Plus: 24 hours a day, 365 days a year
- Characteristic: Availability (in supported hours)
  - Bronze: 98%
  - Silver / Silver Plus\* : 99.50%
  - Gold: 99.90%
  - Platinum / Platinum Plus: 99.90% (Platinum) 99.99% (Platinum Plus)
- Characteristic: Incident resolution times (in supported hours)
  - Bronze:
  - Silver / Silver Plus\* :
  - Gold:
  - Platinum / Platinum Plus:
- Characteristic: Severity 1
  - Bronze: 8 hours
  - Silver / Silver Plus\* : 4 hours
  - Gold: 4 hours
  - Platinum / Platinum Plus: 2 hours
- Characteristic: Severity 2
  - Bronze: 16 hours
  - Silver / Silver Plus\* : 8 hours
  - Gold: 8 hours
  - Platinum / Platinum Plus: 4 hours
- Characteristic: Severity 3
  - Bronze: 40 hours
  - Silver / Silver Plus\* : 20 hours
  - Gold: 10 hours
  - Platinum / Platinum Plus: 8 hours
- Characteristic: Severity 4
  - Bronze: 120 hours
  - Silver / Silver Plus\* : 80 hours
  - Gold: 50 hours
  - Platinum / Platinum Plus: 30 hours
- Characteristic: Severity 5
  - Bronze: 240 hours
  - Silver / Silver Plus\* : 200 hours
  - Gold: 140 hours
  - Platinum / Platinum Plus: 100 hours

\* Silver Plus we respond to severity 1 and severity 2 incidents outside of business hours (8am to 6pm Monday to Friday excluding Bank Holidays).

To find out the service level for a given API, see the API specification in our [API and integration catalogue](https://digital.nhs.uk/developer/api-catalogue).

---

## Statuses

### APIs, message integrations and publish-subscribe events

We tag our [APIs](https://digital.nhs.uk/developer/guides-and-documentation/introduction-to-healthcare-technology/integration-and-apis#apis), [message integrations](https://digital.nhs.uk/developer/guides-and-documentation/introduction-to-healthcare-technology/integration-and-apis#message-integration) and [publish-subscribe events](https://digital.nhs.uk/developer/guides-and-documentation/introduction-to-healthcare-technology/integration-and-apis#publish-subscribe-events) with a status as follows:

- In development - early prototyping - the API is available, and might be available for testing via a sandbox service or an integration environment - but we expect to make breaking changes based on developer feedback
- Beta - the API is available in production - it might still be subject to breaking changes - and its [service level](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#service-levels) can be anything from bronze to platinum
- In production - once out of beta, if we need to make breaking changes, we'll normally publish a new version of the API - we'll only make breaking changes in exceptional circumstances
- Internal - the API is not currently available for integration by external third parties - if you still want to use it, [contact us](https://digital.nhs.uk/developer/help-and-support)
- Under review for deprecation - the API is under review and we're considering deprecating it - if you have any concerns, [contact us](https://digital.nhs.uk/developer/help-and-support)
- Deprecated - the API is still available and service levels still apply, but we plan to retire it at some point - we are unlikely to make any updates and new integrations are not permitted - once deprecated, we will consult with developers before deciding on a retirement date
- Retired - the API is no longer available for use

### API standards

We tag our [API standards](https://digital.nhs.uk/developer/guides-and-documentation/introduction-to-healthcare-technology/integration-and-apis#api-standards) with a status as follows:

- Draft - is still being developed or waiting for assurance or endorsement by qualified bodies
- Active - is stable, maintained and has been assured or endorsed for use by qualified bodies
- Under review for deprecation - is under review and we're considering deprecating it - if you have any concerns, [contact us](https://digital.nhs.uk/developer/help-and-support)
- Deprecated - is an older version of a standard which is being phased out
- Retired - is not being maintained and should not be used

For more details on deprecation and retirement, see our [deprecation and retirement policy](https://digital.nhs.uk/developer/guides-and-documentation/reference-guide#deprecation-and-retirement-policy).

We align these API standard statuses with those found in the [NHS Data Standards Directory](https://data.standards.nhs.uk/).

---

## Version control

All of our RESTful APIs start out with only a single version, and you do not need to specify its version number when you call the API.

Once an API is in production (and it has exited beta) we avoid making any breaking changes, unless absolutely necessary. That means we might add new data fields or add new valid values to code sets, but we do not remove any mandatory fields or change the semantic meaning of any existing fields or code sets.

We use the API path to identify any industry standards and their version, for example, FHIR release 4 as in https://api.service.nhs.uk/personal-demographics/FHIR/R4/.

When we need to make breaking changes to a stable API, we create a new version and run the old and new ones in parallel. To call the new version, you need to use the HTTP accept header to request which API version you want to call. For example, to call version 2, use the accept header application/fhir+json; version=2.

Note this parameter changes for major versions only - version 2, version 3, and so on. This is because we use [semantic versioning](https://semver.org/) definitions, in which a minor version is non-breaking and you do not need to request it.

Last edited: 15 December 2023 12:06 pms
