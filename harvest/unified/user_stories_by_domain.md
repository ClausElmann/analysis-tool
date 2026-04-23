# User Stories — ServiceAlert → GreenAI
**Genereret:** 2026-04-23  
**Kilde:** 630 verified + 89 inferred behaviors + 593 danske komponent-behaviors  
**Total:** 48 user stories

---

## Beskeder & Kommunikation
*Messaging & Communication*  
  
Route: `/messaging`

### [US-001] Manage Messages `P1`
**Story:** Som bruger vil jeg se og søge i beskeder, oprette beskeder og slette beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.
**Acceptkriterier:**
- Brugeren ser en liste over beskeder
- Brugeren kan søge og filtrere beskeder
- Brugeren kan oprette ny/nye beskeder via formular
- Brugeren kan slette beskeder med bekræftelsesdialog

**Blazor:** `Pages/messaging/MessagesPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove message
- [INFERRED] Bruger: User can view and retrieve message
- [INFERRED] Bruger: User can create and submit message

### [US-012] Manage Operationals `P1`
**Story:** Som bruger vil jeg se og søge i driftsdata, oprette driftsdata, redigere driftsdata og slette driftsdata, så jeg kan kommunikere effektivt med kunder og modtagere.
**Acceptkriterier:**
- Brugeren ser en liste over driftsdata
- Brugeren kan søge og filtrere driftsdata
- Brugeren kan oprette ny/nye driftsdata via formular
- Brugeren kan redigere eksisterende driftsdata
- Brugeren kan slette driftsdata med bekræftelsesdialog

**Blazor:** `Pages/messaging/OperationalsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove operational notification
- [INFERRED] Bruger: User can view and retrieve operational notification
- [INFERRED] Bruger: User can create and submit operational notification
- [INFERRED] Bruger: User can update operational notification

### [US-020] Manage Dynamics `P1`
**Story:** Som bruger vil jeg se og søge i dynamiske felter, oprette dynamiske felter, redigere dynamiske felter og slette dynamiske felter, så jeg kan kommunikere effektivt med kunder og modtagere.
**Acceptkriterier:**
- Brugeren ser en liste over dynamiske felter
- Brugeren kan søge og filtrere dynamiske felter
- Brugeren kan oprette ny/nye dynamiske felter via formular
- Brugeren kan redigere eksisterende dynamiske felter
- Brugeren kan slette dynamiske felter med bekræftelsesdialog

**Blazor:** `Pages/messaging/DynamicsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove dynamic notification
- [INFERRED] Bruger: User can view and retrieve dynamic notification
- [INFERRED] Bruger: User can create and submit dynamic notification
- [INFERRED] Bruger: User can update dynamic notification

### [US-023] Manage Webs `P1`
**Story:** Som bruger vil jeg se og søge i web-beskeder, oprette web-beskeder og slette web-beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.
**Acceptkriterier:**
- Brugeren ser en liste over web-beskeder
- Brugeren kan søge og filtrere web-beskeder
- Brugeren kan oprette ny/nye web-beskeder via formular
- Brugeren kan slette web-beskeder med bekræftelsesdialog

**Blazor:** `Pages/messaging/WebsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove web notification channel
- [INFERRED] Bruger: User can view and retrieve web notification channel
- [INFERRED] Bruger: User can create and submit web notification channel

### [US-032] Manage Entries `P1`
**Story:** Som bruger vil jeg se og søge i poster, oprette poster og slette poster, så jeg kan kommunikere effektivt med kunder og modtagere.
**Acceptkriterier:**
- Brugeren ser en liste over poster
- Brugeren kan søge og filtrere poster
- Brugeren kan oprette ny/nye poster via formular
- Brugeren kan slette poster med bekræftelsesdialog

**Blazor:** `Pages/messaging/EntriesPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

### [US-040] Manage Warnings `P1`
**Story:** Som bruger vil jeg se og søge i advarsler, oprette advarsler og redigere advarsler, så jeg kan kommunikere effektivt med kunder og modtagere.
**Acceptkriterier:**
- Brugeren ser en liste over advarsler
- Brugeren kan søge og filtrere advarsler
- Brugeren kan oprette ny/nye advarsler via formular
- Brugeren kan redigere eksisterende advarsler

**Blazor:** `Pages/messaging/WarningsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** create-dialog, edit-dialog, list-with-search, pagination  

### [US-041] Manage Weathers `P1`
**Story:** Som bruger vil jeg se og søge i vejrdata, oprette vejrdata, redigere vejrdata og slette vejrdata, så jeg kan kommunikere effektivt med kunder og modtagere.
**Acceptkriterier:**
- Brugeren ser en liste over vejrdata
- Brugeren kan søge og filtrere vejrdata
- Brugeren kan oprette ny/nye vejrdata via formular
- Brugeren kan redigere eksisterende vejrdata
- Brugeren kan slette vejrdata med bekræftelsesdialog

**Blazor:** `Pages/messaging/WeathersPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

### [US-024] Manage Sms `P2`
**Story:** Som bruger vil jeg se og søge i SMS-beskeder og slette SMS-beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.
**Acceptkriterier:**
- Brugeren ser en liste over SMS-beskeder
- Brugeren kan søge og filtrere SMS-beskeder
- Brugeren kan slette SMS-beskeder med bekræftelsesdialog

**Blazor:** `Pages/messaging/SmsPage.razor`  
**MudBlazor:** MudDataGrid, MudDialog, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove sms notification channel
- [INFERRED] Bruger: User can view and retrieve sms notification channel

### [US-034] Manage Archiveds `P2`
**Story:** Som bruger vil jeg se og søge i arkiverede beskeder, så jeg kan kommunikere effektivt med kunder og modtagere.
**Acceptkriterier:**
- Brugeren ser en liste over arkiverede beskeder
- Brugeren kan søge og filtrere arkiverede beskeder

**Blazor:** `Pages/messaging/ArchivedsPage.razor`  
**MudBlazor:** MudDataGrid, MudTextField  
**Patterns:** list-with-search, pagination  

### [US-037] Manage Status `P2`
**Story:** Som bruger vil jeg se og søge i statusoversigt, så jeg kan kommunikere effektivt med kunder og modtagere.
**Acceptkriterier:**
- Brugeren ser en liste over statusoversigt
- Brugeren kan søge og filtrere statusoversigt

**Blazor:** `Pages/messaging/StatusPage.razor`  
**MudBlazor:** MudDataGrid, MudTextField  
**Patterns:** list-with-search, pagination  

### [US-043] Other Messaging Operations `P2`
**Story:** Som bruger vil jeg arbejde med miscer, så jeg kan kommunikere effektivt med kunder og modtagere.
**Acceptkriterier:**

**Blazor:** `Pages/messaging/MessagingOperationsPage.razor`  
**MudBlazor:**   
**Patterns:**   

## Kunder & Tilmelding
*Customer & Enrollment*  
  
Route: `/customers`

### [US-002] Manage Customers `P1`
**Story:** Som bruger vil jeg se og søge i kunder, oprette kunder, redigere kunder og slette kunder, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
**Acceptkriterier:**
- Brugeren ser en liste over kunder
- Brugeren kan søge og filtrere kunder
- Brugeren kan oprette ny/nye kunder via formular
- Brugeren kan redigere eksisterende kunder
- Brugeren kan slette kunder med bekræftelsesdialog

**Blazor:** `Pages/customers/CustomersPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove customer
- [INFERRED] Bruger: User can view and retrieve customer
- [INFERRED] Bruger: User can modify customer
- [INFERRED] Bruger: User can create and submit customer
- [INFERRED] Bruger: User can update customer

### [US-005] Manage Senders `P1`
**Story:** Som bruger vil jeg se og søge i afsendere, oprette afsendere, redigere afsendere og slette afsendere, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
**Acceptkriterier:**
- Brugeren ser en liste over afsendere
- Brugeren kan søge og filtrere afsendere
- Brugeren kan oprette ny/nye afsendere via formular
- Brugeren kan redigere eksisterende afsendere
- Brugeren kan slette afsendere med bekræftelsesdialog

**Blazor:** `Pages/customers/SendersPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove message sender
- [INFERRED] Bruger: User can view and retrieve message sender
- [INFERRED] Bruger: User can modify message sender
- [INFERRED] Bruger: User can create and submit message sender

### [US-009] Manage Prospects `P1`
**Story:** Som bruger vil jeg se og søge i salgsmuligheder, oprette salgsmuligheder, redigere salgsmuligheder og slette salgsmuligheder, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
**Acceptkriterier:**
- Brugeren ser en liste over salgsmuligheder
- Brugeren kan søge og filtrere salgsmuligheder
- Brugeren kan oprette ny/nye salgsmuligheder via formular
- Brugeren kan redigere eksisterende salgsmuligheder
- Brugeren kan slette salgsmuligheder med bekræftelsesdialog

**Blazor:** `Pages/customers/ProspectsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove potential customer
- [INFERRED] Bruger: User can view and retrieve potential customer
- [INFERRED] Bruger: User can modify potential customer
- [INFERRED] Bruger: User can create and submit potential customer

### [US-016] Manage Contacts `P1`
**Story:** Som bruger vil jeg se og søge i kontakter, oprette kontakter, redigere kontakter og slette kontakter, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
**Acceptkriterier:**
- Brugeren ser en liste over kontakter
- Brugeren kan søge og filtrere kontakter
- Brugeren kan oprette ny/nye kontakter via formular
- Brugeren kan redigere eksisterende kontakter
- Brugeren kan slette kontakter med bekræftelsesdialog

**Blazor:** `Pages/customers/ContactsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove contact person
- [INFERRED] Bruger: User can view and retrieve contact person
- [INFERRED] Bruger: User can create and submit contact person
- [INFERRED] Bruger: User can update contact person

### [US-019] Manage Enrollments `P1`
**Story:** Som bruger vil jeg se og søge i tilmeldinger, oprette tilmeldinger og slette tilmeldinger, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
**Acceptkriterier:**
- Brugeren ser en liste over tilmeldinger
- Brugeren kan søge og filtrere tilmeldinger
- Brugeren kan oprette ny/nye tilmeldinger via formular
- Brugeren kan slette tilmeldinger med bekræftelsesdialog

**Blazor:** `Pages/customers/EnrollmentsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove subscription
- [INFERRED] Bruger: User can view and retrieve subscription
- [INFERRED] Bruger: User can create and submit subscription

### [US-044] Other Customer Operations `P2`
**Story:** Som bruger vil jeg arbejde med miscer, så jeg kan administrere kundernes tilmeldingsforhold og kontaktdata.
**Acceptkriterier:**

**Blazor:** `Pages/customers/CustomerOperationsPage.razor`  
**MudBlazor:**   
**Patterns:**   

## Brugere & Adgang
*User & Access Management*  
  
Route: `/admin`

### [US-003] Manage Profiles `P3`
**Story:** Som bruger vil jeg se og søge i profiler, oprette profiler, redigere profiler og slette profiler, så jeg kan styre brugeradgang og sikkerhed i systemet.
**Acceptkriterier:**
- Brugeren ser en liste over profiler
- Brugeren kan søge og filtrere profiler
- Brugeren kan oprette ny/nye profiler via formular
- Brugeren kan redigere eksisterende profiler
- Brugeren kan slette profiler med bekræftelsesdialog

**Blazor:** `Pages/admin/ProfilesPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove user profile
- [INFERRED] Bruger: User can view and retrieve user profile
- [INFERRED] Bruger: User can create and submit user profile
- [INFERRED] Bruger: User can update user profile

### [US-004] Manage Users `P3`
**Story:** Som bruger vil jeg se og søge i brugere, oprette brugere, redigere brugere og slette brugere, så jeg kan styre brugeradgang og sikkerhed i systemet.
**Acceptkriterier:**
- Brugeren ser en liste over brugere
- Brugeren kan søge og filtrere brugere
- Brugeren kan oprette ny/nye brugere via formular
- Brugeren kan redigere eksisterende brugere
- Brugeren kan slette brugere med bekræftelsesdialog

**Blazor:** `Pages/admin/UsersPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove user account
- [INFERRED] Bruger: User can view and retrieve user account
- [INFERRED] Bruger: User can modify user account
- [INFERRED] Bruger: User can create and submit user account
- [INFERRED] Bruger: User can update user account

### [US-007] Manage Resets `P3`
**Story:** Som bruger vil jeg oprette nulstillinger, så jeg kan styre brugeradgang og sikkerhed i systemet.
**Acceptkriterier:**
- Brugeren kan oprette ny/nye nulstillinger via formular

**Blazor:** `Pages/admin/ResetsPage.razor`  
**MudBlazor:** MudButton, MudDialog, MudForm  
**Patterns:** create-dialog  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can create and submit password reset request

### [US-017] Manage Roles `P3`
**Story:** Som bruger vil jeg se og søge i roller, oprette roller og redigere roller, så jeg kan styre brugeradgang og sikkerhed i systemet.
**Acceptkriterier:**
- Brugeren ser en liste over roller
- Brugeren kan søge og filtrere roller
- Brugeren kan oprette ny/nye roller via formular
- Brugeren kan redigere eksisterende roller

**Blazor:** `Pages/admin/RolesPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** create-dialog, edit-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can view and retrieve user role
- [INFERRED] Bruger: User can create and submit user role
- [INFERRED] Bruger: User can update user role

### [US-022] Manage Maps `P3`
**Story:** Som bruger vil jeg se og søge i kortvisning, oprette kortvisning, redigere kortvisning og slette kortvisning, så jeg kan styre brugeradgang og sikkerhed i systemet.
**Acceptkriterier:**
- Brugeren ser en liste over kortvisning
- Brugeren kan søge og filtrere kortvisning
- Brugeren kan oprette ny/nye kortvisning via formular
- Brugeren kan redigere eksisterende kortvisning
- Brugeren kan slette kortvisning med bekræftelsesdialog

**Blazor:** `Pages/admin/MapsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudPaper, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, map-view, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove geographic map
- [INFERRED] Bruger: User can view and retrieve geographic map
- [INFERRED] Bruger: User can create and submit geographic map
- [INFERRED] Bruger: User can update geographic map

### [US-031] Manage Customers `P3`
**Story:** Som bruger vil jeg se og søge i kunder, så jeg kan styre brugeradgang og sikkerhed i systemet.
**Acceptkriterier:**
- Brugeren ser en liste over kunder
- Brugeren kan søge og filtrere kunder

**Blazor:** `Pages/admin/CustomersPage.razor`  
**MudBlazor:** MudDataGrid, MudTextField  
**Patterns:** list-with-search, pagination  

### [US-035] Manage Receivers `P3`
**Story:** Som bruger vil jeg oprette modtagere, så jeg kan styre brugeradgang og sikkerhed i systemet.
**Acceptkriterier:**
- Brugeren kan oprette ny/nye modtagere via formular

**Blazor:** `Pages/admin/ReceiversPage.razor`  
**MudBlazor:** MudButton, MudDialog, MudForm  
**Patterns:** create-dialog  

### [US-036] Manage Configurations `P3`
**Story:** Som bruger vil jeg se og søge i konfigurationer, oprette konfigurationer og slette konfigurationer, så jeg kan styre brugeradgang og sikkerhed i systemet.
**Acceptkriterier:**
- Brugeren ser en liste over konfigurationer
- Brugeren kan søge og filtrere konfigurationer
- Brugeren kan oprette ny/nye konfigurationer via formular
- Brugeren kan slette konfigurationer med bekræftelsesdialog

**Blazor:** `Pages/admin/ConfigurationsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove system configuration
- [INFERRED] Bruger: User can view and retrieve system configuration
- [INFERRED] Bruger: User can create and submit system configuration

### [US-038] Manage Conversations `P3`
**Story:** Som bruger vil jeg se og søge i samtaler og oprette samtaler, så jeg kan styre brugeradgang og sikkerhed i systemet.
**Acceptkriterier:**
- Brugeren ser en liste over samtaler
- Brugeren kan søge og filtrere samtaler
- Brugeren kan oprette ny/nye samtaler via formular

**Blazor:** `Pages/admin/ConversationsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudTextField  
**Patterns:** create-dialog, list-with-search, pagination  

### [US-039] Manage Ftps `P3`
**Story:** Som bruger vil jeg se og søge i FTP-filer, oprette FTP-filer, redigere FTP-filer og slette FTP-filer, så jeg kan styre brugeradgang og sikkerhed i systemet.
**Acceptkriterier:**
- Brugeren ser en liste over FTP-filer
- Brugeren kan søge og filtrere FTP-filer
- Brugeren kan oprette ny/nye FTP-filer via formular
- Brugeren kan redigere eksisterende FTP-filer
- Brugeren kan slette FTP-filer med bekræftelsesdialog

**Blazor:** `Pages/admin/FtpsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

### [US-048] Other User Operations `P3`
**Story:** Som bruger vil jeg arbejde med miscer, så jeg kan styre brugeradgang og sikkerhed i systemet.
**Acceptkriterier:**

**Blazor:** `Pages/admin/UserOperationsPage.razor`  
**MudBlazor:**   
**Patterns:**   

## Adresser & Data
*Address & Data*  
  
Route: `/addresses`

### [US-013] Manage Groups `P3`
**Story:** Som bruger vil jeg se og søge i grupper, oprette grupper og slette grupper, så jeg kan håndtere og validere adressedata korrekt.
**Acceptkriterier:**
- Brugeren ser en liste over grupper
- Brugeren kan søge og filtrere grupper
- Brugeren kan oprette ny/nye grupper via formular
- Brugeren kan slette grupper med bekræftelsesdialog

**Blazor:** `Pages/addresses/GroupsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove recipient group
- [INFERRED] Bruger: User can view and retrieve recipient group
- [INFERRED] Bruger: User can create and submit recipient group

### [US-014] Manage Corrections `P3`
**Story:** Som bruger vil jeg oprette korrektioner og slette korrektioner, så jeg kan håndtere og validere adressedata korrekt.
**Acceptkriterier:**
- Brugeren kan oprette ny/nye korrektioner via formular
- Brugeren kan slette korrektioner med bekræftelsesdialog

**Blazor:** `Pages/addresses/CorrectionsPage.razor`  
**MudBlazor:** MudButton, MudDialog, MudForm, MudIconButton  
**Patterns:** confirm-delete-dialog, create-dialog  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove address correction
- [INFERRED] Bruger: User can create and submit address correction

### [US-015] Manage Receivers `P3`
**Story:** Som bruger vil jeg se og søge i modtagere og oprette modtagere, så jeg kan håndtere og validere adressedata korrekt.
**Acceptkriterier:**
- Brugeren ser en liste over modtagere
- Brugeren kan søge og filtrere modtagere
- Brugeren kan oprette ny/nye modtagere via formular

**Blazor:** `Pages/addresses/ReceiversPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudTextField  
**Patterns:** create-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can view and retrieve notification recipient
- [INFERRED] Bruger: User can create and submit notification recipient

### [US-021] Manage Gdprs `P3`
**Story:** Som bruger vil jeg se og søge i GDPR-håndtering, oprette GDPR-håndtering, redigere GDPR-håndtering og slette GDPR-håndtering, så jeg kan håndtere og validere adressedata korrekt.
**Acceptkriterier:**
- Brugeren ser en liste over GDPR-håndtering
- Brugeren kan søge og filtrere GDPR-håndtering
- Brugeren kan oprette ny/nye GDPR-håndtering via formular
- Brugeren kan redigere eksisterende GDPR-håndtering
- Brugeren kan slette GDPR-håndtering med bekræftelsesdialog

**Blazor:** `Pages/addresses/GdprsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove privacy consent record
- [INFERRED] Bruger: User can view and retrieve privacy consent record
- [INFERRED] Bruger: User can create and submit privacy consent record
- [INFERRED] Bruger: User can update privacy consent record

### [US-026] Manage Address `P3`
**Story:** Som bruger vil jeg se og søge i adresser, oprette adresser og redigere adresser, så jeg kan håndtere og validere adressedata korrekt.
**Acceptkriterier:**
- Brugeren ser en liste over adresser
- Brugeren kan søge og filtrere adresser
- Brugeren kan oprette ny/nye adresser via formular
- Brugeren kan redigere eksisterende adresser

**Blazor:** `Pages/addresses/AddressPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudPaper, MudTextField  
**Patterns:** create-dialog, edit-dialog, list-with-search, map-view, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can view and retrieve address
- [INFERRED] Bruger: User can create and submit address
- [INFERRED] Bruger: User can update address

### [US-027] Manage Stds `P3`
**Story:** Som bruger vil jeg oprette standardindstillinger og slette standardindstillinger, så jeg kan håndtere og validere adressedata korrekt.
**Acceptkriterier:**
- Brugeren kan oprette ny/nye standardindstillinger via formular
- Brugeren kan slette standardindstillinger med bekræftelsesdialog

**Blazor:** `Pages/addresses/StdsPage.razor`  
**MudBlazor:** MudButton, MudDialog, MudForm, MudIconButton  
**Patterns:** confirm-delete-dialog, create-dialog  

### [US-028] Manage Localizeds `P3`
**Story:** Som bruger vil jeg oprette sprogoversættelser, så jeg kan håndtere og validere adressedata korrekt.
**Acceptkriterier:**
- Brugeren kan oprette ny/nye sprogoversættelser via formular

**Blazor:** `Pages/addresses/LocalizedsPage.razor`  
**MudBlazor:** MudButton, MudDialog, MudForm  
**Patterns:** create-dialog  

### [US-030] Manage Imports `P3`
**Story:** Som bruger vil jeg se og søge i dataimport, oprette dataimport og slette dataimport, så jeg kan håndtere og validere adressedata korrekt.
**Acceptkriterier:**
- Brugeren ser en liste over dataimport
- Brugeren kan søge og filtrere dataimport
- Brugeren kan oprette ny/nye dataimport via formular
- Brugeren kan slette dataimport med bekræftelsesdialog

**Blazor:** `Pages/addresses/ImportsPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

### [US-042] Manage Statstidendes `P3`
**Story:** Som bruger vil jeg se og søge i statstidendeer, oprette statstidendeer og slette statstidendeer, så jeg kan håndtere og validere adressedata korrekt.
**Acceptkriterier:**
- Brugeren ser en liste over statstidendeer
- Brugeren kan søge og filtrere statstidendeer
- Brugeren kan oprette ny/nye statstidendeer via formular
- Brugeren kan slette statstidendeer med bekræftelsesdialog

**Blazor:** `Pages/addresses/StatstidendesPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

### [US-046] Other Address Operations `P3`
**Story:** Som bruger vil jeg arbejde med miscer, så jeg kan håndtere og validere adressedata korrekt.
**Acceptkriterier:**

**Blazor:** `Pages/addresses/AddressOperationsPage.razor`  
**MudBlazor:**   
**Patterns:**   

## Økonomi & Drift
*Finance & Operations*  
  
Route: `/finance`

### [US-008] Manage Sales `P3`
**Story:** Som bruger vil jeg se og søge i salgsdata, oprette salgsdata, redigere salgsdata og slette salgsdata, så jeg kan holde styr på økonomi og driftsprocesser.
**Acceptkriterier:**
- Brugeren ser en liste over salgsdata
- Brugeren kan søge og filtrere salgsdata
- Brugeren kan oprette ny/nye salgsdata via formular
- Brugeren kan redigere eksisterende salgsdata
- Brugeren kan slette salgsdata med bekræftelsesdialog

**Blazor:** `Pages/finance/SalesPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove sales record
- [INFERRED] Bruger: User can view and retrieve sales record
- [INFERRED] Bruger: User can create and submit sales record
- [INFERRED] Bruger: User can update sales record

### [US-010] Manage Salaries `P3`
**Story:** Som bruger vil jeg se og søge i lønsedler, så jeg kan holde styr på økonomi og driftsprocesser.
**Acceptkriterier:**
- Brugeren ser en liste over lønsedler
- Brugeren kan søge og filtrere lønsedler

**Blazor:** `Pages/finance/SalariesPage.razor`  
**MudBlazor:** MudDataGrid, MudTextField  
**Patterns:** list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can view and retrieve payroll period

### [US-011] Manage Absences `P3`
**Story:** Som bruger vil jeg se og søge i fraværsregistreringer, oprette fraværsregistreringer, redigere fraværsregistreringer og slette fraværsregistreringer, så jeg kan holde styr på økonomi og driftsprocesser.
**Acceptkriterier:**
- Brugeren ser en liste over fraværsregistreringer
- Brugeren kan søge og filtrere fraværsregistreringer
- Brugeren kan oprette ny/nye fraværsregistreringer via formular
- Brugeren kan redigere eksisterende fraværsregistreringer
- Brugeren kan slette fraværsregistreringer med bekræftelsesdialog

**Blazor:** `Pages/finance/AbsencesPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove employee absence
- [INFERRED] Bruger: User can view and retrieve employee absence
- [INFERRED] Bruger: User can modify employee absence
- [INFERRED] Bruger: User can create and submit employee absence

### [US-018] Manage Invoices `P3`
**Story:** Som bruger vil jeg se og søge i fakturaer, så jeg kan holde styr på økonomi og driftsprocesser.
**Acceptkriterier:**
- Brugeren ser en liste over fakturaer
- Brugeren kan søge og filtrere fakturaer

**Blazor:** `Pages/finance/InvoicesPage.razor`  
**MudBlazor:** MudDataGrid, MudTextField  
**Patterns:** list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can view and retrieve invoice

### [US-029] Manage Employees `P3`
**Story:** Som bruger vil jeg se og søge i medarbejdere og oprette medarbejdere, så jeg kan holde styr på økonomi og driftsprocesser.
**Acceptkriterier:**
- Brugeren ser en liste over medarbejdere
- Brugeren kan søge og filtrere medarbejdere
- Brugeren kan oprette ny/nye medarbejdere via formular

**Blazor:** `Pages/finance/EmployeesPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudTextField  
**Patterns:** create-dialog, list-with-search, pagination  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can view and retrieve employee
- [INFERRED] Bruger: User can create and submit employee

### [US-033] Manage Drives `P3`
**Story:** Som bruger vil jeg se og søge i fildrev, oprette fildrev og slette fildrev, så jeg kan holde styr på økonomi og driftsprocesser.
**Acceptkriterier:**
- Brugeren ser en liste over fildrev
- Brugeren kan søge og filtrere fildrev
- Brugeren kan oprette ny/nye fildrev via formular
- Brugeren kan slette fildrev med bekræftelsesdialog

**Blazor:** `Pages/finance/DrivesPage.razor`  
**MudBlazor:** MudButton, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, list-with-search, pagination  

### [US-047] Other Finance Operations `P3`
**Story:** Som bruger vil jeg arbejde med miscer, så jeg kan holde styr på økonomi og driftsprocesser.
**Acceptkriterier:**

**Blazor:** `Pages/finance/FinanceOperationsPage.razor`  
**MudBlazor:**   
**Patterns:**   

## Analyse & Rapportering
*Analytics & Reporting*  
  
Route: `/analytics`

### [US-006] Manage Benchmarks `P3`
**Story:** Som bruger vil jeg se og søge i benchmarks, oprette benchmarks, redigere benchmarks og slette benchmarks, så jeg kan få indsigt i systemaktivitet og performance.
**Acceptkriterier:**
- Brugeren ser en liste over benchmarks
- Brugeren kan søge og filtrere benchmarks
- Brugeren kan oprette ny/nye benchmarks via formular
- Brugeren kan redigere eksisterende benchmarks
- Brugeren kan slette benchmarks med bekræftelsesdialog

**Blazor:** `Pages/analytics/BenchmarksPage.razor`  
**MudBlazor:** MudButton, MudCard, MudChart, MudDataGrid, MudDialog, MudForm, MudIconButton, MudTextField  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog, list-with-search, pagination, stats-cards  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove performance benchmark
- [INFERRED] Bruger: User can view and retrieve performance benchmark
- [INFERRED] Bruger: User can modify performance benchmark
- [INFERRED] Bruger: User can create and submit performance benchmark

### [US-025] Manage Causes `P3`
**Story:** Som bruger vil jeg oprette årsagskoder, redigere årsagskoder og slette årsagskoder, så jeg kan få indsigt i systemaktivitet og performance.
**Acceptkriterier:**
- Brugeren kan oprette ny/nye årsagskoder via formular
- Brugeren kan redigere eksisterende årsagskoder
- Brugeren kan slette årsagskoder med bekræftelsesdialog

**Blazor:** `Pages/analytics/CausesPage.razor`  
**MudBlazor:** MudButton, MudDialog, MudForm, MudIconButton  
**Patterns:** confirm-delete-dialog, create-dialog, edit-dialog  

**Behaviors fra høst:**
- [INFERRED] Bruger: User can remove benchmark cause
- [INFERRED] Bruger: User can create and submit benchmark cause
- [INFERRED] Bruger: User can update benchmark cause

### [US-045] Other Analytics Operations `P3`
**Story:** Som bruger vil jeg arbejde med miscer, så jeg kan få indsigt i systemaktivitet og performance.
**Acceptkriterier:**

**Blazor:** `Pages/analytics/AnalyticsOperationsPage.razor`  
**MudBlazor:**   
**Patterns:**   
