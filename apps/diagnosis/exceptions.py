"""
Domain exceptions for diagnosis business rules — design_doc §4.3
Mapped to HTTP responses in config/exception_handler.py.
Phase 4 will fully activate DuplicateSubmissionError in DiagnosisService.
"""


class DuplicateSubmissionError(Exception):
    """
    design_doc §4.3 — raised when same patient is submitted within 1 hour.
    Maps to HTTP 400 with error code DUPLICATE_SUBMISSION.
    """
    def __init__(self, message, original_diagnosis_id, original_submitted_at):
        self.message = message
        self.original_diagnosis_id = original_diagnosis_id
        self.original_submitted_at = original_submitted_at
        super().__init__(message)


class DiagnosisStatusError(Exception):
    """
    Raised when an operation is attempted on a job in an invalid status.
    e.g. submitting a doctor opinion when status != awaiting_doctor_input.
    Maps to HTTP 400 with error code INVALID_STATUS.
    """
    pass
