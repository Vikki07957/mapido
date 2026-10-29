# Optional MongoDB

MongoDB is not used by MAPIDO's working implementation. MySQL stores every record needed to authorize or complete a ride, including chat messages in the included demo.

If a later deployment adds MongoDB, it may store append-only activity logs or denormalized notification payloads. Do not store the authoritative ride, seat count, booking status, review eligibility or payment/contribution agreement there. Do not require MongoDB to approve a booking or send a booking response; MySQL transactions remain the source of truth. If an optional MongoDB write fails, log the failure and keep the committed MySQL operation intact. Avoid dual-write workflows that can partially confirm a booking.