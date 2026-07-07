# Model Leakage Audit

Delay features exclude actual arrival, actual delay, and future state. Current prototype split is random and should become group-aware by shipment_id as real history grows.

SLA features exclude actual SLA outcome and actual arrival. The prototype SLA target is synthetic; future training should use out-of-fold delay predictions if predicted delay is included.

Carbon target is formula-derived, so high R2 means agreement with prototype emission logic, not field-validated emissions.

Maintenance remains rules-first and does not claim mechanical failure prediction.
