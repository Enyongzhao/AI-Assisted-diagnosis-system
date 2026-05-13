"""
Repository layer for Report — design_doc §5.1 reports table.
Stores the S3 key (or local path) after PDF generation.
Pre-signed URL is generated on demand in the /report/ view.
"""
from apps.diagnosis.models import Report


class ReportRepository:

    @staticmethod
    def create(diagnosis_id, s3_key: str, file_size_bytes: int):
        """Create and return the Report record after a PDF is generated and uploaded."""
        return Report.objects.create(
            diagnosis_id=diagnosis_id,
            s3_key=s3_key,
            file_size_bytes=file_size_bytes,
        )

    @staticmethod
    def get_by_diagnosis(diagnosis_id):
        """Returns Report for the given diagnosis_id, or None."""
        try:
            return Report.objects.get(diagnosis_id=diagnosis_id)
        except Report.DoesNotExist:
            return None
