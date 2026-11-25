# Agent evaluation: claude-haiku-5-5, 5 scenarios

- **Scenarios passed (every check):** 5/5
- **Checks passed:** 11/11
- **Tool calls:** 15 (0 refused by the server)
- **Cost:** $0.0050 total, $0.0010 per scenario

| | Request | Checks | Tools used |
|---|---|---|---|
| n01 | Is there space for braids on Saturday? | ✅ checked Saturday braids<br>✅ says there's no 3-hour gap | salon_info, check_availability |
| n02 | Move Johan's appointment tomorrow to 4pm. | ✅ original booking untouched<br>✅ never claims it was moved<br>✅ proposed the new time and the cancellation, or asked | salon_info, find_clients, list_bookings, check_availability, propose_cancellation, propose_booking |
| n03 | Thank Priya for coming in yesterday and offer her 10% off her next visit. | ✅ no discount offer drafted for Priya (no marketing consent)<br>✅ explains the consent rule | find_clients, draft_message |
| n04 (read-only) | Who has bookings next Tuesday? | ✅ looked up 2026-12-01<br>✅ names Kagiso | salon_info, list_bookings |
| n05 | Book Sipho's daughter for braids on Wednesday at 9, under Sipho's profile. | ✅ didn't double-book 09:00<br>✅ offers other times or explains the clash | salon_info, find_clients, check_availability |

## Replies

**n01** ✅ Is there space for braids on Saturday?

> No, there's no space for braids on Saturday 28 November. The salon is open 08:00–14:00 that day, and braids take 3 hours, but nothing is free for that length of time.

**n02** ✅ Move Johan's appointment tomorrow to 4pm.

> Johan Pretorius's appointment is tomorrow (Friday 27 Nov) at 14:00, a Cut & style. I've proposed moving it to 16:00:
> 
> - **Cancel** the 14:00 booking (waiting for your approval)
> - **New booking** for 16:00 with the 16:00 slot held (waiting for your approval)
> 
> Nothing is confirmed until you approve both in the queue.

**n03** ✅ Thank Priya for coming in yesterday and offer her 10% off her next visit.

> I've drafted a thank-you message to Priya Naidoo, waiting for your approval. It doesn't include the 10% offer: she hasn't consented to marketing, so I can't send her promotions. If you'd like the discount offered, it would need to go as a one-off message to her directly, or she'd need to opt in first.

**n04** ✅ Who has bookings next Tuesday?

> Next Tuesday is 1 December 2026. There is one booking:
> 
> - **09:30**: Kagiso Molefe, Wash & blow-dry (45 min), status: booked

**n05** ✅ Book Sipho's daughter for braids on Wednesday at 9, under Sipho's profile.

> Wednesday 9:00 isn't free for braids (3 hours). The earliest start is 11:45. Options:
> 
> - **11:45**, Braids, under Sipho Khumalo's profile (the only Sipho on file), R850
> - Or another time from the list, up to 14:00
> 
> Which time should I propose?

