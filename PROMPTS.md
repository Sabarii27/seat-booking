
## AI-Assisted Development Notes

I used AI tools during the development of this project to help with planning, implementation, debugging, testing, and reviewing the code.

I did not use one prompt to generate the entire project at once. I worked through the requirements step by step and used AI to help with individual parts of the system. I also reviewed and changed generated code when it did not match the requirements or when I needed a different approach.

The prompts below represent the main prompts and instructions I used during the development process.

---

## 1. Understanding the Requirement and Planning to build  the Project

### Prompt

I have a technical assessment to build a seat booking system.

The requirements are:

- There is one event.
- There are 10 rows and 12 seats in each row, so 120 seats total.
- A seat can be available, held, or booked.
- A user can select a maximum of 4 seats.
- When the user clicks Hold, the selected seats should be locked for 5 minutes.
- All selected seats must be held together. If even one seat is unavailable, the hold should fail.
- If the user doesn't confirm within 5 minutes, the hold should expire and the seats should become available again.
- When a hold is confirmed, create a booking with a booking reference.
- The frontend should show the seat map and countdown.
- The seat status should update automatically without manually refreshing the page.
- The backend must handle two users trying to take the same seat at the same time.
- I need a proper concurrency solution at the database level, not just a frontend check.
- I also need tests, including a concurrent request test.
- The API should include:
  GET /seats
  POST /holds
  DELETE /holds/{id}
  POST /bookings
  GET /bookings

I am using Python/FastAPI, React and MySQL.

First, help me plan the project structure, database design, API flow and concurrency strategy before writing the implementation. Keep the solution simple enough for a technical assessment but make sure the important edge cases are handled.

### What I did

I used the response as the initial design direction and then implemented the project in smaller parts instead of asking AI to generate the entire application in one shot.

---

## 2. Database Design and Backend Structure

### Prompt

Now help me design the database for this seat booking system. I need to store seats, holds, the seats belonging to each hold, and bookings.

Please think about:

- how to represent available, held and booked seats
- how to track hold expiration
- how to associate multiple seats with one hold
- how to prevent the same seat from being booked twice
- what database constraints and indexes would be useful
- how the schema should support transactions and row locking in MySQL

After explaining the design, suggest a clean backend structure with models, services and API routes.

Don't over-engineer it. This is a coding assessment, so I want a design that is easy to understand and explain in the README.

### What I did

I used the database design as the base for the backend models and API structure. I kept the schema focused on the actual requirements instead of adding unnecessary authentication, payment or admin functionality.

---

## 3. Implementing the Hold Logic

### Prompt

I want to implement the seat hold functionality now. A user can select up to 4 seats and create a hold for 5 minutes.

The important requirement is that the operation must be all-or-nothing. For example, if the user requests seats 5, 6 and 7 and seat 6 is already booked or actively held, none of the three seats should be held.

Please implement this using a database transaction.

I especially want to understand how to use MySQL row-level locking such as SELECT ... FOR UPDATE so that two requests cannot successfully take the same seat.

Please make the solution safe when two users send hold requests for the same seat at nearly the same time.

Also explain why a normal Python lock or checking the seat status before starting the transaction is not enough.

### What I did

I used the transaction and database locking approach for the seat-mutating operations. The important part was making the database the source of truth instead of relying on frontend state or an in-memory Python lock.

---

## 4. Reviewing the Concurrency Logic

### Prompt

Please review the concurrency logic of my seat booking implementation carefully.

I am concerned about this situation:

User A and User B both request the same seat at almost exactly the same time.

I need exactly one request to succeed and the other request to fail.

Check my implementation for race conditions such as:

- checking availability before acquiring a lock
- locking different seats in different orders
- creating duplicate holds
- committing part of a multi-seat hold
- booking a seat that another transaction already took
- relying on application-level locks instead of database locking

If there is a problem, explain the problem first and then show me the safest correction.

Keep the solution compatible with MySQL and explain the reasoning in simple terms because I need to describe this in an interview.

### What I did

I used AI mainly as a reviewer here rather than blindly accepting the generated implementation. I checked the transaction boundaries and made sure the seat rows are locked consistently before making the availability decision.

I also paid attention to deterministic seat ordering so that concurrent requests are less likely to create lock-ordering problems.

---

## 5. Handling Expired Holds

### Prompt

The requirement says that a hold should expire after 5 minutes and the seats should become available again.

Help me implement this correctly.

I don't want the system to depend only on the frontend countdown because the frontend cannot be trusted.

Please suggest a simple backend/database approach for expired holds.

It should work even if:

- the user closes the browser
- the frontend stops polling
- another user requests a seat whose hold has already expired

I want expired holds to actually be cleaned up or resolved, not just displayed as expired in the UI.

Explain the approach and tell me where the cleanup should happen.

### What I did

I treated the backend as authoritative for expiration. The frontend countdown is only for user feedback. The backend checks expiration when processing seat operations so an expired hold cannot continue blocking a seat.

---

## 6. Implementing Booking Confirmation

### Prompt

Now help me implement the booking confirmation flow.

The user should only be able to confirm their own active hold.

When a hold is confirmed:

- verify that the hold exists
- verify that it has not expired
- verify that the hold is still active
- create a booking with a unique booking reference
- mark the associated seats as booked
- make sure the whole operation is atomic

If anything fails, the transaction should roll back.

Please also think about what should happen if two requests try to confirm the same hold at almost the same time.

I want the database transaction to be responsible for maintaining the correct state.

### What I did

I implemented booking confirmation as a transactional operation so that creating the booking and changing the seats happen together.

---

## 7. Building the React Seat Map

### Prompt

Now help me build the React frontend for the seat booking system.

I need a simple seat map showing 10 rows and 12 seats per row.

Each seat should visually show whether it is:

- available
- selected
- held
- booked

The user should be able to select a maximum of 4 available seats.

When Hold is clicked, send the selected seat IDs to the backend.

After a successful hold, show a 5-minute countdown.

Please keep the UI simple and suitable for a coding assessment. Focus more on correct behavior than fancy styling.

Also make sure the frontend handles backend errors properly, especially when a seat was available when the page loaded but another user took it before the current user clicked Hold.

### What I did

I used React state for the current UI selection and backend data for the actual seat state. I also added error handling so that a failed hold does not leave the frontend thinking that seats were successfully held.

---

## 8. Automatic Seat Updates and Polling

### Prompt

I need the seat map to update automatically when another user changes a seat.

I don't want to add WebSockets because it is not necessary for this assessment.

Can you implement simple polling from React?

For example, fetch the seat list every few seconds and update the UI.

Please make sure:

- the polling interval is cleaned up when the component unmounts
- it does not create multiple intervals accidentally
- the current user's countdown still works
- selected seats are handled safely if their state changes on the backend
- the backend remains the source of truth

Also explain briefly in the README why polling was chosen instead of WebSockets for this assignment.

### What I did

I used polling because it was enough for the assessment requirements and kept the implementation simpler. The frontend periodically fetches the current seat state from the backend.

---

## 9. Testing the Booking System

### Prompt

Help me create tests for the main seat booking behavior.

I want tests for at least:

1. getting the seats
2. successfully holding available seats
3. holding more than 4 seats should fail
4. holding a booked seat should fail
5. multi-seat hold should be all-or-nothing
6. expired holds should become available
7. successful booking confirmation
8. invalid or expired booking confirmation should fail

The tests should check the actual API behavior and database state where appropriate.

Please keep the tests readable because I want someone reviewing the repository to understand what each test is proving.

### What I did

I used these cases to verify the normal booking flow and the important edge cases instead of only testing successful requests.

---

## 10. Concurrent Booking Test

### Prompt

The assessment specifically requires a test that fires concurrent booking requests against the same seat and proves that exactly one request wins.

Help me write this test properly.

I don't want a fake sequential test.

I want two requests to be sent concurrently against the same seat/booking operation.

The final assertions should prove:

- exactly one request succeeds
- the other request fails
- the seat ends up booked only once
- there is no duplicate booking for the same seat

Please explain how the test creates real concurrency and why the database transaction/locking strategy makes the result deterministic.

Also tell me if SQLite could give a different result from MySQL, because the actual application uses MySQL.

### What I did

I added a dedicated concurrency test instead of relying only on normal sequential tests. I used it to verify the main invariant that two competing requests cannot both successfully claim the same seat.

---

## 11. README and Technical Explanation

### Prompt

Please help me write the README for this project.

The README needs to explain:

- what the project does
- technologies used
- project structure
- setup instructions
- how to run backend and frontend
- database setup
- API endpoints
- database schema
- how the 5-minute hold works
- how expired holds are cleaned up
- how concurrent requests are handled
- how the database prevents double booking
- why row-level locking/transactions are used
- how the concurrency test works
- what I would improve if I had more time

The concurrency explanation is especially important because the assessment says they care more about concurrency reasoning than extra features.

Please write it clearly enough that a reviewer can understand the design without reading every file.

### What I did

I used AI to help structure the README, then reviewed it against the actual implementation so that the documentation did not claim features that were not present.

---

## 12. Final Code Review

### Prompt

I want to do a final review before submitting this assessment.

Review the project as if you are a senior engineer evaluating a coding assignment.

Check for:

- broken API behavior
- incorrect seat state transitions
- race conditions
- transaction problems
- expired hold problems
- duplicate booking possibilities
- frontend/backend mismatch
- missing validation
- incorrect error responses
- bad React state handling
- polling cleanup problems
- test quality
- README accuracy
- unnecessary code
- security or reliability issues that are relevant to this assignment

Do not suggest adding features that are outside the assessment requirements.

For each issue, explain:
1. what is wrong
2. why it matters
3. how I should fix it

Prioritize correctness and concurrency over styling.

### What I did

I used the AI as a final reviewer and made corrections where the suggestions matched the actual requirements. I did not add unrelated features just to make the project larger.

---

## 13. When AI Output Needed Correction

During development, some AI-generated approaches needed to be reviewed or changed.

The main correction I focused on was concurrency.

A simple approach such as:

1. check whether a seat is available
2. create a hold
3. update the seat

is not safe by itself because two requests can perform the availability check before either one updates the database.

I therefore made the database transaction and row-level locking the important part of the solution.

I also made sure that the frontend countdown is not treated as the authority for hold expiration. The backend must decide whether a hold is still valid.

Another important correction was making sure multiple seats in one hold are processed atomically. If one requested seat is unavailable, the entire hold should fail instead of partially succeeding.

---

## 14. AI Usage Approach

I used AI as a development assistant rather than treating it as a one-click code generator.

My general workflow was:

1. Understand the requirement myself.
2. Ask AI for a possible design or implementation.
3. Review the generated code.
4. Run the application/tests.
5. Identify problems or missing requirements.
6. Ask AI targeted questions about the problem.
7. Modify or override the suggested solution when necessary.
8. Test the updated implementation again.
9. Document the final design in the README.

The most important area where I used this approach was the concurrency handling, because correctness depends on transaction boundaries and database locking rather than simply making the API appear to work in normal cases.

---

## 15. Final Note

These prompts represent the main stages of my AI-assisted development process. I used AI for planning, implementation support, debugging, testing and review, while making the final decisions about the implementation and checking the behavior against the assessment requirements.