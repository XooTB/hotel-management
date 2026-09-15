# Diagrams

All diagrams are [Mermaid](https://mermaid.js.org/) — they render directly on GitHub, GitLab and in VS Code
(Markdown Preview Mermaid Support), or paste them into <https://mermaid.live> to export PNG/SVG for the report.

## 1. Entity–relationship diagram

```mermaid
erDiagram
    USER ||--o{ SHIFT : "works"
    USER ||--o{ HOUSEKEEPING_TASK : "is assigned"
    USER |o--o{ RESERVATION : "creates (walk-in/phone)"
    USER |o--o{ ORDER : "takes"

    ROOM_TYPE }o--o{ AMENITY : "offers"
    ROOM_TYPE ||--|{ ROOM : "has"
    ROOM_TYPE ||--o{ RESERVATION : "is booked as"
    ROOM |o--o{ RESERVATION : "is assigned at check-in"
    ROOM ||--o{ HOUSEKEEPING_TASK : "needs"

    RESERVATION ||--o| INVOICE : "is billed by"
    INVOICE ||--|{ INVOICE_LINE : "contains"
    RESERVATION |o--o{ ORDER : "is charged"

    MENU_CATEGORY ||--|{ MENU_ITEM : "groups"
    ORDER ||--|{ ORDER_ITEM : "contains"
    MENU_ITEM ||--o{ ORDER_ITEM : "is ordered as"

    USER {
        bigint id PK
        string username UK
        string first_name
        string last_name
        string email
        string role "manager | receptionist | housekeeping | restaurant"
        string phone
        bool is_active
    }
    ROOM_TYPE {
        bigint id PK
        string name UK
        string slug UK
        decimal nightly_rate
        smallint capacity
        string bed_type
        smallint size_sqm
        image image
        bool is_active
    }
    AMENITY {
        bigint id PK
        string name UK
    }
    ROOM {
        bigint id PK
        string number UK
        smallint floor
        bigint room_type_id FK
        string status "available | occupied | cleaning | maintenance"
    }
    RESERVATION {
        bigint id PK
        string reference UK "e.g. GA7K2QXM"
        bigint room_type_id FK
        bigint room_id FK "nullable"
        string guest_name
        string guest_email
        string guest_phone
        date check_in
        date check_out "CHECK check_out > check_in"
        smallint adults
        smallint children
        decimal nightly_rate "rate snapshot"
        string status "confirmed | checked_in | checked_out | cancelled | no_show"
        string source "online | walk_in | phone"
        datetime created_at
    }
    INVOICE {
        bigint id PK
        string number UK "INV-YYYY-00001"
        bigint reservation_id FK,UK
        string status "unpaid | paid"
        decimal tax_rate
        string payment_method "cash | card | other"
        datetime issued_at
        datetime paid_at
    }
    INVOICE_LINE {
        bigint id PK
        bigint invoice_id FK
        string description
        int quantity
        decimal unit_price
    }
    HOUSEKEEPING_TASK {
        bigint id PK
        bigint room_id FK
        string task_type "cleaning | inspection | maintenance"
        string priority "low | normal | high"
        string status "pending | in_progress | done"
        bigint assigned_to_id FK
    }
    MENU_CATEGORY {
        bigint id PK
        string name UK
        smallint position
    }
    MENU_ITEM {
        bigint id PK
        bigint category_id FK
        string name
        decimal price
        bool is_available
    }
    ORDER {
        bigint id PK
        string order_type "dine_in | room_service"
        string table_number
        bigint reservation_id FK "nullable"
        bool charge_to_room
        bool is_paid
        string status "placed | preparing | served | cancelled"
    }
    ORDER_ITEM {
        bigint id PK
        bigint order_id FK
        bigint menu_item_id FK
        smallint quantity
        decimal unit_price "price snapshot"
    }
    SHIFT {
        bigint id PK
        bigint staff_id FK
        date date
        time start_time
        time end_time
    }
```

## 2. Use-case diagram

```mermaid
flowchart LR
    guest([Guest])
    reception([Receptionist])
    housekeeper([Housekeeping])
    chef([Restaurant staff])
    manager([Manager])

    subgraph Public website
        UC1(Browse rooms & amenities)
        UC2(Search availability)
        UC3(Book a room)
        UC4(Look up booking by reference + email)
        UC5(Cancel booking)
    end

    subgraph Staff dashboard
        UC6(Create walk-in / phone reservation)
        UC7(Check guest in & assign room)
        UC8(Check guest out)
        UC9(Settle invoice)
        UC10(Update room status)
        UC11(Manage housekeeping tasks)
        UC12(Take dine-in / room-service order)
        UC13(Manage menu)
        UC14(View own shifts)
        UC15(Manage rooms, room types & rates)
        UC16(Manage staff accounts & shifts)
        UC17(View reports)
    end

    guest --- UC1 & UC2 & UC3 & UC4 & UC5
    reception --- UC6 & UC7 & UC8 & UC9 & UC10 & UC11 & UC12 & UC14
    housekeeper --- UC10 & UC11 & UC14
    chef --- UC12 & UC13 & UC14
    manager --- UC15 & UC16 & UC17
    manager -. inherits every staff role .- reception
    UC8 -. includes .-> UC9
```

## 3. Class diagram (domain layer)

```mermaid
classDiagram
    class User {
        +Role role
        +is_manager() bool
        +has_role(*roles) bool
    }
    class RoomType {
        +name
        +nightly_rate
        +capacity
        +get_absolute_url()
    }
    class Room {
        +number
        +floor
        +Status status
    }
    class Reservation {
        +reference
        +check_in
        +check_out
        +nightly_rate
        +Status status
        +nights() int
        +room_total() Decimal
        +can_cancel() bool
        +can_check_in() bool
        +can_check_out() bool
    }
    class Invoice {
        +number
        +Status status
        +tax_rate
        +subtotal() Decimal
        +tax() Decimal
        +total() Decimal
    }
    class InvoiceLine {
        +description
        +quantity
        +unit_price
        +amount() Decimal
    }
    class Order {
        +OrderType order_type
        +Status status
        +charge_to_room
        +total() Decimal
    }
    class HousekeepingTask {
        +TaskType task_type
        +Priority priority
        +Status status
    }
    class ReservationServices {
        <<module>>
        +available_count(room_type, check_in, check_out) int
        +search_availability(check_in, check_out, guests) list
        +create_reservation(...) Reservation
        +assignable_rooms(reservation) QuerySet
        +check_in(reservation, room)
        +check_out(reservation) Invoice
        +cancel(reservation, by_staff)
        +mark_no_show(reservation)
    }
    class BillingServices {
        <<module>>
        +build_invoice(reservation) Invoice
        +mark_paid(invoice, method)
    }
    class HousekeepingServices {
        <<module>>
        +create_task(**fields) HousekeepingTask
        +set_status(task, status)
    }

    RoomType "1" --> "*" Room
    RoomType "1" --> "*" Reservation
    Room "0..1" <-- "*" Reservation
    Reservation "1" --> "0..1" Invoice
    Invoice "1" *-- "*" InvoiceLine
    Reservation "0..1" <-- "*" Order
    Room "1" --> "*" HousekeepingTask
    User "0..1" <-- "*" HousekeepingTask
    ReservationServices ..> Reservation
    ReservationServices ..> BillingServices : check_out uses
    ReservationServices ..> HousekeepingTask : creates cleaning task
    BillingServices ..> Invoice
    HousekeepingServices ..> Room : frees room
```

## 4. Sequence — guest books online

```mermaid
sequenceDiagram
    actor Guest
    participant Web as Website views
    participant Svc as reservations.services
    participant DB as PostgreSQL
    participant Mail as Email backend

    Guest->>Web: GET /search/?check_in&check_out&guests
    Web->>Svc: search_availability()
    Svc->>DB: count rooms & overlapping stays per night
    Web-->>Guest: room types with price and rooms left (HTMX partial)
    Guest->>Web: POST /rooms/<slug>/book/ (guest details)
    Web->>Svc: create_reservation()
    activate Svc
    Svc->>DB: BEGIN; SELECT ... FOR UPDATE on room type
    Svc->>Svc: validate dates, capacity, availability
    alt room still available
        Svc->>DB: INSERT reservation (reference, rate snapshot); COMMIT
        Svc-->>Web: Reservation
        Web->>Mail: confirmation with reference
        Web-->>Guest: 302 → confirmation page
    else sold out meanwhile
        Svc-->>Web: BookingError
        Web-->>Guest: form redisplayed with error
    end
    deactivate Svc
```

## 5. Sequence — check-out

```mermaid
sequenceDiagram
    actor Receptionist
    participant View as reservations.views.check_out
    participant Res as reservations.services
    participant Bill as billing.services
    participant DB as PostgreSQL

    Receptionist->>View: POST /dashboard/reservations/<ref>/check-out/
    View->>Res: check_out(reservation)
    Res->>DB: BEGIN
    Res->>Bill: build_invoice(reservation)
    Bill->>DB: INSERT invoice + room-nights line
    Bill->>DB: INSERT one line per room-charged order
    Res->>DB: reservation.status = checked_out
    Res->>DB: room.status = cleaning
    Res->>DB: INSERT housekeeping task (high priority)
    Res->>DB: COMMIT
    View-->>Receptionist: 302 → invoice page
    Receptionist->>View: POST /dashboard/billing/<id>/pay/ (cash/card)
    View->>Bill: mark_paid()
```

## 6. State diagrams

```mermaid
stateDiagram-v2
    direction LR
    [*] --> Confirmed: booked online / by staff
    Confirmed --> CheckedIn: check-in (room assigned)
    Confirmed --> Cancelled: guest or staff cancels
    Confirmed --> NoShow: staff marks no-show
    CheckedIn --> CheckedOut: check-out (invoice raised)
    CheckedOut --> [*]
    Cancelled --> [*]
    NoShow --> [*]
```

```mermaid
stateDiagram-v2
    direction LR
    Available --> Occupied: guest checked in
    Occupied --> Cleaning: guest checked out
    Cleaning --> Available: all housekeeping tasks done
    Available --> Maintenance: maintenance task / manual
    Maintenance --> Available: task done / manual
```
