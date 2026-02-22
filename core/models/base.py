from django.db import models
import uuid
from django.conf import settings

class BaseModel(models.Model):
    """
    Abstract base model that provides common fields for all models.
    Fields include:
    - id: UUID primary key
    - created_at: Timestamp when record was created
    - updated_at: Timestamp when record was last updated
    - updated_by: Reference to user who last updated the record
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated_by"
    )
    is_deleted = models.BooleanField(
        default=False,
        help_text="Logical deletion flag"
    )

    class Meta:
        abstract = True

    def soft_delete(self, updated_by=None):
        """Soft delete the dish by marking it as deleted."""
        self.is_deleted = True
        self.updated_by = updated_by
        self.save(update_fields=["is_deleted", "updated_by"])

    def un_delete(self, updated_by=None):
        """Undelete the dish by marking it as not deleted."""
        self.is_deleted = False
        self.updated_by = updated_by
        self.save(update_fields=["is_deleted", "updated_by"])

    @classmethod
    def get_by_id(cls, id: uuid.UUID):
        """
        Get an object by its ID.
        Returns None if the object does not exist or is deleted.
        """
        try:
            return cls.objects.get(id=id, is_deleted=False)
        except cls.DoesNotExist:
            return None

    @property
    def date(self):
        """
        Returns the date part of the created_at timestamp.
        Useful for displaying just the date without time.
        """
        return self.created_at.astimezone().date()

    @property
    def time(self):
        """
        Returns the time part of the created_at timestamp.
        Useful for displaying just the time without date.
        """
        return self.created_at.astimezone().time()
