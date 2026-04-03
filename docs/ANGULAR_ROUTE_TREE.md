# Angular Route Tree — ServiceAlert.Web

**Extracted:** 2026-04-02  
**Source:** `c:\Udvikling\sms-service\ServiceAlert.Web\ClientApp\src`  
**Purpose:** Reference for designing Blazor routing with deep linking

---

## Overview — 4 Angular Applications

| App | Bundle | Auth required | Path base |
|-----|--------|--------------|-----------|
| `ServiceAlert.Web` (main) | Main app | Yes (MSAL + AppCanActivateGuard) | `/` |
| `subscription-app` | Separate | No (anonymous enrollment) | `/` |
| `quick-response` | Separate | No (anonymous tag response) | `/` |
| `iframe-modules` | Separate | No (anonymous embedded iframes) | `/iFrame/...` |

---

## APP 1 — ServiceAlert.Web (main authenticated app)

Root routes defined in `app.config.ts`, feature routes in `features-routing.module.ts`.

```
path: /frontpage
  component: FrontpageComponent (lazy)
  params: []
  guards: []

path: / (empty, pathMatch: full)
  component: FrontpageComponent (lazy)
  params: []
  guards: [initialRedirectGuard — inline CanActivateFn]
  note: redirects to /broadcasting if logged in, else /frontpage

path: (shell — all feature routes)
  canActivateChild: [AppCanActivateGuard]
  children:

  - path: /login
    component: BiLoginComponent (lazy)
    params: []
    guards: []

  - path: /transparent-login
    component: TransparentLoginComponent (lazy)
    params: []
    guards: []

  - path: /reset-password
    component: PasswordResetCreateComponent (lazy)
    params: []
    guards: [AppCanActivateGuard]

  - path: /new-password
    component: PasswordResetCreateComponent (lazy)
    params: []
    guards: [AppCanActivateGuard]

  - path: /terms-and-conditions
    component: TermsAndConditionsComponent (eager)
    params: []
    guards: []

  - path: /support
    component: SupportComponent (lazy)
    params: []
    guards: []

  - path: /unavailable
    component: UnavailableComponent (lazy, @globals)
    params: []
    guards: []

  - path: /confirm-twitter
    component: ConfirmTwitterComponent (lazy)
    params: []
    guards: []

  - path: /broadcasting
    module: BroadcastingModule (lazy)
    params: []
    guards: [canMatch: limitedUserGuardFunc(true)]

  - path: /broadcasting-limited
    component: BroadcastingLimitedComponent (lazy)
    params: []
    guards: [canMatch: limitedUserGuardFunc(false)]

  - path: /create-message
    component: MessageWizardLimitedComponent (lazy)
    params: []
    guards: [canMatch: limitedUserGuardFunc(false), canActivateLimitedWizardGuardFn]

  - path: /message-wizard
    module: MessageWizardModule (lazy)
    params: []
    guards: [canActivate: CanActivateWizardRoute, canMatch: UserRoleGuard(ManageMessages) + limitedUserGuardFunc(true)]
    children:
      - path: /message-wizard/by-address
        component: ByAddressComponent (lazy)
        params: []
        guards: [canActivate: ProfileRoleRouteGuard(CanSendByAddressSelection), canActivateWizardRecipientSelectionRoutes]
      - path: /message-wizard/by-excel
        component: ByExcelComponent (lazy)
        params: []
        guards: [canActivate: ProfileRoleRouteGuard(CanUploadStreetList), canActivateWizardRecipientSelectionRoutes]
      - path: /message-wizard/by-map
        component: ByMapComponent (lazy)
        params: []
        guards: [canActivate: ProfileRoleRouteGuard(CanSendByMap), canActivateWizardRecipientSelectionRoutes]
      - path: /message-wizard/by-level
        component: ByLevelComponent (lazy)
        params: []
        guards: []
      - path: /message-wizard/by-municipality
        component: ByMunicipalityComponent (lazy)
        params: []
        guards: []
      - path: /message-wizard/std-receivers
        component: StdReceiversComponent (lazy)
        params: []
        guards: [canActivate: canActivateWizardRecipientSelectionRoutes]
      - path: /message-wizard/std-receivers-ext
        component: StdReceiversExtendedComponent (lazy)
        params: []
        guards: [canActivate: canActivateWizardRecipientSelectionRoutes, ProfileService.doesProfileHaveRole(StdReceiverExtended)]
      - path: /message-wizard/write-message
        component: WriteMessageWizardStepComponent (lazy)
        params: []
        guards: []
      - path: /message-wizard/confirm
        component: ConfirmComponent (lazy)
        params: []
        guards: []
      - path: /message-wizard/complete
        component: BroadcastCompleteComponent (lazy)
        params: []
        guards: [canMatch: canActivateWizardCompleteRoute, canDeactivate: canDeactivateWizardCompleteRoute]
      - path: (empty) → redirectTo /broadcasting

  - path: /message-wizard-scheduled
    module: MessageWizardScheduledModule (lazy)
    params: []
    guards: [canActivate: CanActivateWizardRoute, canMatch: UserRoleGuard(ManageMessages)]
    children:
      - path: /message-wizard-scheduled/by-address
        component: ByAddressComponent (lazy)
        params: []
        guards: [canActivate: canActivateRerouteFunc, ProfileRoleRouteGuard(CanSendByAddressSelection)]
      - path: /message-wizard-scheduled/std-receivers
        component: StdReceiversComponent (lazy)
        params: []
        guards: [canActivate: canActivateRerouteFunc]
      - path: /message-wizard-scheduled/by-excel
        component: ByExcelComponent (eager within module)
        params: []
        guards: [canActivate: canActivateRerouteFunc, ProfileRoleRouteGuard(CanUploadStreetList)]
      - path: /message-wizard-scheduled/by-map
        component: ByMapComponent (eager within module)
        params: []
        guards: [canActivate: canActivateRerouteFunc, ProfileRoleRouteGuard(CanSendByMap)]
      - path: /message-wizard-scheduled/by-level
        component: ByLevelComponent (lazy)
        params: []
        guards: [canActivate: canActivateRerouteFunc]
      - path: /message-wizard-scheduled/by-municipality
        component: ByMunicipalityComponent (lazy)
        params: []
        guards: [canActivate: canActivateRerouteFunc]
      - path: /message-wizard-scheduled/schedule-setup
        component: MessageSchedulingSetupComponent (eager within module)
        params: []
        guards: [canActivate: canActivateRerouteFunc]
      - path: /message-wizard-scheduled/write-message
        component: WriteScheduledMessageComponent (eager within module)
        params: []
        guards: [UNKNOWN]
      - path: /message-wizard-scheduled/confirm
        component: UNKNOWN
        params: []
        guards: [canActivate: canActivateRerouteFunc]

  - path: /message-wizard-stencil
    module: MessageWizardScheduledModule (lazy — same module reused)
    params: []
    guards: [canActivate: CanActivateWizardRoute, canMatch: UserRoleGuard(ManageMessages)]
    data: { isCreatingStencil: true }
    children: same as /message-wizard-scheduled

  - path: /my-user
    module: my-user.routes (lazy standalone)
    params: []
    guards: []
    children:
      - path: (shell) → MyUserComponent (lazy)
        children:
          - path: (empty) → redirectTo user-infoEdit
          - path: /my-user/user-infoEdit
            component: UserInfoEditComponent (lazy)
            params: []
            guards: []
          - path: /my-user/security
            component: UserSecurityComponent (lazy)
            params: []
            guards: []

  - path: /status
    module: status.routes (lazy standalone)
    params: []
    guards: [canMatch: UserRoleGuard(ManageReports)]
    children:
      - path: /status
        component: StatusComponent (lazy)
        params: []
        guards: []
      - path: /status/:smsGroupId
        component: StatusDetailsComponent (eager within module)
        params: [smsGroupId]
        guards: []
        children:
          - path: /status/:smsGroupId/overview
            component: OverviewComponent (lazy)
            params: [smsGroupId]
          - path: /status/:smsGroupId/addresses
            component: StatusAddressesComponent (lazy)
            params: [smsGroupId]
          - path: /status/:smsGroupId/statusReport
            component: StatusReportComponent (lazy)
            params: [smsGroupId]
          - path: /status/:smsGroupId/message-content
            component: StatusMessageContentComponent (lazy)
            params: [smsGroupId]
          - path: (empty) → redirectTo overview

  - path: /sms-conversations
    module: SmsConversationsModule (lazy)
    params: []
    guards: [canMatch: ProfileRoleRouteGuard(SmsConversations)]
    children:
      - path: (empty)
        component: SmsConversationsComponent (eager within module)

  - path: /admin
    module: AdministrationModule (lazy)
    params: []
    guards: [canMatch: limitedUserGuardFunc(true)]
    children:

      - path: /admin (empty, pathMatch full)
        component: AdministrationComponent (eager)
        params: []
        guards: []

      - path: /admin/benchmark
        module: BenchmarkModule (lazy)
        params: []
        guards: [canMatch: UserRoleGuard(Benchmark)]
        children:
          - path: (shell) → BenchmarkMainComponent
            - path: (empty) → redirectTo index
            - path: /admin/benchmark/index
              component: BenchmarkIndexComponent (eager)
            - path: /admin/benchmark/create
              component: BenchmarkCreateEditMainComponent (eager)
            - path: /admin/benchmark/edit/:id
              component: BenchmarkCreateEditMainComponent (eager)
              params: [id]
            - path: /admin/benchmark/statistics
              component: BenchmarkStatisticsComponent (lazy)
            - path: /admin/benchmark/kpis
              component: BenchmarkKpisComponent (lazy)
            - path: /admin/benchmark/administration
              component: BenchmarkCausesComponent (lazy)
            - path: /admin/benchmark/overview
              component: BenchmarkOverviewComponent (eager)
            - path: /admin/benchmark/settings
              component: BenchmarkSettingsComponent (lazy)

      - path: /admin/std-receivers-setup
        module: StdReceiversAdminModule (lazy)
        params: []
        guards: [canMatch: UserRoleGuard(StandardReceivers)]
        children:
          - path: (shell) → MainStdReceiversComponent (lazy)
            - path: (empty) → redirectTo std-receivers
            - path: /admin/std-receivers-setup/std-receivers
              module: create-edit-delete-receivers.routes (lazy)
              note: internal routes UNKNOWN
              params: contains :receiverId per RouteNames
            - path: /admin/std-receivers-setup/receiver-groups
              module: receiver-groups.routes (lazy)
              note: internal routes UNKNOWN
              params: contains :groupId per RouteNames
            - path: /admin/std-receivers-setup/profile-mapping
              component: ProfilesAndGroupsComponent (lazy)
            - path: /admin/std-receivers-setup/receiver-upload
              component: ReceiversUploadComponent (lazy)
            - path: /admin/std-receivers-setup/subscription-module
              module: SubscriptionModuleSetupModule (lazy)
              note: internal routes UNKNOWN
            - path: /admin/std-receivers-setup/keywords-module
              component: GroupKeywordSetupComponent (lazy)
            - path: /admin/std-receivers-setup/ad-provisioning
              component: AdProvisioningComponent (lazy)

      - path: /admin/customer
        module: CustomerAdminModule (lazy)
        params: []
        guards: [canMatch: UserRoleGuard(CustomerSetup)]
        note: module not read — routes inferred from RouteNames
        children:
          - /admin/customer/settings
          - /admin/customer/users
          - /admin/customer/users/create
          - /admin/customer/users/:userId
            params: [userId]
            children:
              - /admin/customer/users/:userId/user-profiles
              - /admin/customer/users/:userId/user-roles
          - /admin/customer/profiles
          - /admin/customer/profiles/create-profile
          - /admin/customer/profiles/edit-profile (+ /:id implied)
            children:
              - info | roles | account | api-keys | users | map
              - social-media | email2sms | ready-reports | statstidende
              - ftp-setup | distribution
          - /admin/customer/social-media
          - /admin/customer/gdpr
          - /admin/customer/sms-conversations

      - path: /admin/message-examples
        component: MessageExamplesMainComponent (lazy)
        params: []
        guards: []

      - path: /admin/message-templates
        module: MessageTemplatesModule (lazy)
        params: []
        guards: [canMatch: UserRoleGuard(MessageTemplates)]
        note: internal routes inferred from RouteNames only
        children:
          - /admin/message-templates/templates
          - /admin/message-templates/merge-fields
          - /admin/message-templates/template-access
          - /admin/message-templates/weather-warnings
          - /admin/message-templates/warning-templates
          - /admin/message-templates/trimble-templates

      - path: /admin/searching
        module: BiSearchingModule (lazy)
        params: []
        guards: [canMatch: UserRoleGuard(Searching)]
        note: internal routes inferred from RouteNames only
        children:
          - /admin/searching/phone-email
          - /admin/searching/address
          - /admin/searching/report

      - path: /admin/statstidende
        module: statstidende.routes (lazy standalone)
        params: []
        guards: [canMatch: UserRoleGuard(CanSetupStatstidende)]
        children:
          - /admin/statstidende/receivers

      - path: /admin/web-messages
        module: WebMessagesModule (lazy)
        params: []
        guards: [canMatch: UserRoleGuard(WEBMessages)]
        note: internal routes inferred from RouteNames only
        children:
          - /admin/web-messages/messages
          - /admin/web-messages/iFrame-driftstatus
          - /admin/web-messages/iFrame-driftstatus-map
          - /admin/web-messages/iFrame-driftstatus-setup
          - /admin/web-messages/iFrame-driftstatus-map-setup

      - path: /admin/subscribe-unsubscribe
        module: SubscribeUnsubscribeModule (lazy)
        params: []
        guards: [canMatch: UserRoleGuard(SubscriptionModule)]
        note: internal routes inferred from RouteNames only
        children:
          - /admin/subscribe-unsubscribe/iFrame-subscription
          - /admin/subscribe-unsubscribe/iFrame-subscription-setup
          - /admin/subscribe-unsubscribe/subscription-report
          - /admin/subscribe-unsubscribe/subscription-notification
          - /admin/subscribe-unsubscribe/excel-upload
          - /admin/subscribe-unsubscribe/enrollment-app

      - path: /admin/scheduled-broadcasts
        module: ScheduledBroadcastModule (lazy)
        params: []
        guards: [canMatch: UserRoleGuard(CanCreateScheduledBroadcasts)]
        children:
          - path: (shell) → ScheduledBroadcastMainComponent
            - path: (empty) → redirectTo list
            - path: /admin/scheduled-broadcasts/calendar
              component: ScheduledBroadcastsComponent (eager)
            - path: /admin/scheduled-broadcasts/list
              component: ScheduledBroadcastListComponent (eager)

      - path: /admin/critical-addresses
        module: critical-addresses.routing (lazy standalone)
        params: []
        guards: [canMatch: UserRoleGuard(CanManageCriticalAddresses)]
        children:
          - /admin/critical-addresses/addresses
          - /admin/critical-addresses/industry-codes
          - /admin/critical-addresses/excel-upload

      - path: /admin/file-management
        module: file-management.routes (lazy standalone)
        params: []
        guards: [canMatch: UserRoleGuard(ManageMessages)]
        children:
          - /admin/file-management/profile-storage-files

      Super-admin sub-routes (all under canActivate: UserRoleGuard(SuperAdmin)):

      - path: /admin/super/translations
        component: TranslationManagementComponent (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin), canDeactivate: AppCanDeactivateGuard]

      - path: /admin/super/communication
        module: CommunicationModule (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        children:
          - /admin/super/communication/operationalMessages
          - /admin/super/communication/news-letter
          - /admin/super/communication/data-processor-agreements
          - /admin/super/communication/data-processor-agreements/create
          - /admin/super/communication/data-processor-agreements/edit

      - path: /admin/super/pos-lists
        module: PosListsModule (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        children:
          - /admin/super/pos-lists/upload-pos-list
          - /admin/super/pos-lists/municipality-setup
          - /admin/super/pos-lists/uploaded-pos-lists
          - /admin/super/pos-lists/positive-lookup
          - /admin/super/pos-lists/negative-list
          - /admin/super/pos-lists/import-corrections
          - /admin/super/pos-lists/import-fof-corrections
          - /admin/super/pos-lists/additional-import-addresses
          - /admin/super/pos-lists/index

      - path: /admin/super/customers
        module: SuperCustomersModule (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        children:
          - /admin/super/customers/create-customer
          - /admin/super/customers/map
          - /admin/super/customers/:id
            params: [id]
            children:
              - /admin/super/customers/:id/profiles
              - /admin/super/customers/:id/users
              - /admin/super/customers/:id/settings
              - /admin/super/customers/:id/admin
              - /admin/super/customers/:id/ftpSettings
              - /admin/super/customers/:id/api-keys
              - /admin/super/customers/:id/gdpr
              - /admin/super/customers/:id/contact-persons
              - /admin/super/customers/:id/contact-persons/create
              - /admin/super/customers/:id/contact-persons/edit/:contactId
                params: [id, contactId]

      - path: /admin/super/users
        module: SuperUsersModule (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        children:
          - /admin/super/users/users-index
          - /admin/super/users/profile-selection
          - /admin/super/users/contact-persons-index
          - /admin/super/users/:id/detail
            params: [id]
            children:
              - /admin/super/users/:id/detail/data
              - /admin/super/users/:id/detail/subscriptions

      - path: /admin/super/settings
        module: SuperAdminSettingsModule (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        children:
          - /admin/super/settings/packages-setup
          - /admin/super/settings/functions
          - /admin/super/settings/sales-info
          - /admin/super/settings/profile-roles-country-mapping
          - /admin/super/settings/user-roles-country-mapping

      - path: /admin/super/log
        component: BiLogComponent (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]

      - path: /admin/super/invoicing
        module: invoicing.routes (lazy standalone)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        children:
          - /admin/super/invoicing/economic-transfer
          - /admin/super/invoicing/framweb-export
          - /admin/super/invoicing/load-invoices
          - /admin/super/invoicing/accrual
          - /admin/super/invoicing/summary
          - /admin/super/invoicing/budget-follow-up
          - /admin/super/invoicing/product-catalog
          - /admin/super/invoicing/mappings
          - /admin/super/invoicing/upload

      - path: /admin/super/phonenumberproviders
        module: PhoneNumberImportModule (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        children:
          - /admin/super/phonenumberproviders/providers
          - /admin/super/phonenumberproviders/providers/create
          - /admin/super/phonenumberproviders/providers/:id/detail
            params: [id]
          - /admin/super/phonenumberproviders/imports
          - /admin/super/phonenumberproviders/lookupSwedishSkipList

      - path: /admin/super/monitoring
        module: MonitoringModule (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        children:
          - /admin/super/monitoring/dashboard
          - /admin/super/monitoring/map
          - /admin/super/monitoring/nodeJobs

      - path: /admin/super/enrollment
        module: EnrollmentModule (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        children:
          - path: (shell) → EnrollmentMainComponent
            - path: (empty) → redirectTo senders
            - /admin/super/enrollment/senders
              component: SendersMainComponent (eager)
            - /admin/super/enrollment/senders/create
              component: CreateEditSenderComponent (eager)
            - /admin/super/enrollment/senders/edit/:id
              component: CreateEditSenderComponent (eager)
              params: [id]
            - /admin/super/enrollment/statistics
              component: EnrollmentStatisticsComponent (eager)
            - /admin/super/enrollment/reports
              component: EnrollmentReportsComponent (eager)

      - path: /admin/super/hr
        module: HumanResourceModule (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        children:
          - path: (shell) → HumanResourceMainComponent
            - path: (empty) → redirectTo absences
            - /admin/super/hr/absences       → AbsencesComponent (lazy)
            - /admin/super/hr/holidays       → HolidaysComponent (lazy)
            - /admin/super/hr/salary         → SalaryOverviewComponent (lazy)
            - /admin/super/hr/driving        → DrivingsComponent (lazy)
            - /admin/super/hr/employees      → EmployeesComponent (lazy)

      - path: /admin/internal-reports
        module: InternalReportsModule (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        note: path does NOT have "super/" prefix — unlike all other super-admin routes
        children:
          - /admin/internal-reports/virtual-phone-numbers
          - /admin/internal-reports/failed-ad-logins
          - /admin/internal-reports/nudging-report
          - /admin/internal-reports/webinar-report
          - /admin/internal-reports/krr-kofuvi-statistics

      - path: /admin/super/salesforce
        module: SalesforceModule (lazy)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        children:
          - path: (shell) → SalesforceMainComponent
            - path: (empty) → redirectTo opportunities
            - /admin/super/salesforce/opportunities        → SalesforceOpportunitiesComponent
            - /admin/super/salesforce/forecast-evaluation → SalesforceForecastEvaluationComponent
            - /admin/super/salesforce/pipeline            → SalesforcePipelineComponent
            - /admin/super/salesforce/development         → SalesforceDevelopmentComponent
            - /admin/super/salesforce/modified            → SalesforceModifiedComponent

      - path: /admin/super/inboundCall/:phone
        component: InboundCallRedirectComponent (eager)
        params: [phone]
        guards: [UserRoleGuard(SuperAdmin)]

      - path: /admin/super/mapLayers
        module: map-layers.routes (lazy standalone)
        params: []
        guards: [UserRoleGuard(SuperAdmin)]
        children:
          - /admin/super/mapLayers/:id
            params: [id]
            children:
              - /admin/super/mapLayers/:id/access

  - path: /pipeline
    module: PipelineModule (lazy)
    params: []
    guards: [canMatch: UserRoleGuard(SuperAdmin)]
    children:
      - path: /pipeline (empty)
        component: PipelineMainComponent (eager)
      - path: /pipeline/prospects
        module: customer-prospect-create-edit.routing (lazy)
        params: []
        guards: []
        known children from RouteNames:
          - /pipeline/prospects/create
          - /pipeline/prospects/:prospectId
            params: [prospectId]
            children:
              - /pipeline/prospects/:prospectId/edit-info
              - /pipeline/prospects/:prospectId/edit-tasks
      - path: /pipeline/create-customer/:prospectId
        component: CreateCustomerByProspectComponent (lazy)
        params: [prospectId]
        guards: []
      - path: /pipeline/edit-termination/:customerId
        component: CustomerTerminationEditComponent (lazy)
        params: [customerId]
        guards: []
      - path: /pipeline/edit-process-tasks/:processType/:customerId
        component: ProcessTasksEditComponent (lazy)
        params: [processType, customerId]
        guards: []

  - path: **
    redirectTo: /broadcasting
```

---

## APP 2 — subscription-app (anonymous enrollment, separate bundle)

Routes in `features.routes.ts` + `enrollment-steps.routes.ts`.

```
path: /enrollment
  module: EnrollmentStepsModule (lazy)
  params: []
  guards: [canActivate: enrollmentStepsRouteGuardFn — blocks if enrolleeCreationDate already set]
  children:
    - path: (shell) → EnrollmentStepsMainComponent
      data: { state: "enrollment" }
      children:
        - path: (empty) → redirectTo step-1
        - /enrollment/step-1
          component: MobileAndPinStepComponent (eager)
          params: []
          guards: []
        - /enrollment/step-2
          component: EnterAddressComponent (eager)
          params: []
          guards: [canActivate: AppCanActivateGuard]
        - /enrollment/step-3
          component: SenderSelectionComponent (eager)
          params: []
          guards: [canActivate: AppCanActivateGuard]

path: /about
  component: AboutPageComponent (eager)
  params: []
  guards: []

path: /privacy-policy
  component: PrivacyPolicyMainComponent (eager)
  params: []
  guards: []

path: /terms-and-conditions
  component: EnTermsAndConditionsMainComponent (lazy)
  params: []
  guards: []

path: /my-senders
  component: MySendersComponent (lazy)
  params: []
  guards: [canActivate: AppCanActivateGuard]

path: /login
  module: EnLoginModule (lazy)
  params: []
  guards: []
  note: internal routes UNKNOWN

path: /unsubscribe-sender
  module: UnsubscribeSenderModule (lazy)
  params: []
  guards: []
  note: internal routes UNKNOWN

path: **
  component: WelcomePageComponent (lazy)
```

---

## APP 3 — quick-response (anonymous smart-response, separate bundle)

Routes in `app.config.ts` (inline, no separate routing file).

```
path: / (empty)
  component: QuickResponseAppComponent (eager)
  params: []
  guards: []

path: /:tag
  component: QuickResponseAppComponent (eager)
  params: [tag]
  guards: []
```

---

## APP 4 — iframe-modules (anonymous embedded iframes, separate bundle)

Routes resolved via `loadRouteConfigFunc()` — dynamic switch on `window.location.pathname` before router initializes. Each pathname loads a single-route module (`path: ""`).

```
path: /unavailable
  component: UnavailableComponent (lazy, @globals)
  params: []
  guards: []

path: / (empty) → dynamic switch based on actual URL pathname:

  case /iFrame/driftstatus
    component: IframeDriftstatusComponent (lazy)
    params: []
    guards: []

  case /iFrame/driftstatus-map
    component: IframeDriftstatusMapComponent (lazy)
    params: []
    guards: []

  case /iFrame/subscription
    component: IframeSubscriptionComponent (lazy)
    params: []
    guards: []

  case /iFrame/std-receivers
    component: IframeSubscriptionStdReceiverComponent (lazy)
    params: []
    guards: []
```

---

## UNKNOWNS

1. **`/enrollment-dashboard`** — referenced in `RouteNames.routeNotRequiringProfile()` but no route definition found in any routing file.
2. **`super/prospects`** — defined in `RouteNames.adminRoutes.subRoutes.superAdmin` but not present in `super-administration-routing.module.ts`. May be removed or dead code.
3. **`/admin/customer`** internal routes — `customer-admin.module` not read; all paths inferred from `RouteNames` constants only.
4. **`/message-wizard-scheduled/write-message`** guard — routing file truncated; guard presence unknown.
5. **`/message-wizard-scheduled/confirm`** component name — file truncated; component unknown.
6. **`/admin/std-receivers-setup/std-receivers`** sub-routes — `create-edit-delete-receivers.routes` not read.
7. **`/admin/std-receivers-setup/receiver-groups`** sub-routes — `receiver-groups.routes` not read.
8. **`/admin/std-receivers-setup/subscription-module`** sub-routes — `subscription-module-setup.module` not read.
9. **`/login` (subscription-app)** internal routes — `EnLoginModule` not read.
10. **`/unsubscribe-sender`** internal routes — `UnsubscribeSenderModule` not read.
11. **`/admin/web-messages`, `/admin/subscribe-unsubscribe`, `/admin/message-templates`, `/admin/searching`, `/admin/statstidende`, `/admin/critical-addresses`, `/admin/file-management`** — module files not read; all child paths inferred from `RouteNames` only; actual component names and guards unknown.
12. **`/admin/super/customers`, `/admin/super/users`, `/admin/super/settings`, `/admin/super/phonenumberproviders`, `/admin/super/monitoring`, `/admin/super/communication`, `/admin/super/pos-lists`, `/admin/super/invoicing`, `/admin/super/mapLayers`** — module files not read; all child routes inferred from `RouteNames` only.
13. **`/pipeline/prospects`** sub-routes — `customer-prospect-create-edit.routing` not read.
14. **iframe-modules dynamic routing** — not standard Angular router lazy-loading; path matching is imperative (`switch` on pathname). No deep-linking within individual iframe modules (all use `path: ""`).
