class SubscribedFieldMixin:
    """
    Миксин для добавления поля is_subscribed.
    """

    def get_is_subscribed(self, obj):
        annotated_value = getattr(obj, 'is_subscribed', None)
        if annotated_value is not None:
            return annotated_value
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False

        return request.user.subscriptions.filter(pk=obj.pk).exists()
