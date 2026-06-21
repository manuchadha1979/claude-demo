import json

class MessageEncoder(json.JSONEncoder):
    def default(self, obj):
        # Replace 'TextBlock' with the actual class type if imported
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

