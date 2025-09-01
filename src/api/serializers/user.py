from django.contrib.auth.models import Group, User

from api.lib.serializers import SimpleHyperlinkedModelSerializer


# pylint: disable=too-few-public-methods,too-many-ancestors
class SimpleOwnerSerializer(SimpleHyperlinkedModelSerializer):
    """
    serializer for owner aka user
    limited to not expose to much information
    """

    # pylint: disable=too-many-ancestors
    class Meta:
        model = User
        fields = (
            "id",
            "username",
        )


# pylint: disable=too-few-public-methods,too-many-ancestors
class SimpleGroupSerializer(SimpleHyperlinkedModelSerializer):
    """
    serializer for group
    """

    # pylint: disable=too-many-ancestors
    class Meta:
        model = Group
        fields = (
            "id",
            "name",
        )
