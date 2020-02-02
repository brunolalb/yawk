from PIL import Image


class ffi():
    def __init__(self):
        self.is_centered = False
        self.is_halfway = False

    @staticmethod
    def new(arg1):
        return lib


class lib():
    def __init__(self):
        pass

    @staticmethod
    def new(arg1):
        return ffi

    @staticmethod
    def fbink_open():
        return True

    @staticmethod
    def fbink_init(arg1, arg2):
        pass

    @staticmethod
    def fbink_get_state(arg1, arg2):
        pass

    @staticmethod
    def fbink_close(arg1):
        pass

    @staticmethod
    def fbink_cls(arg1, arg2):
        pass

    @staticmethod
    def fbink_print_image(arg1, image_path, arg3, arg4, arg5):
        img = Image.open(r"{}".format(image_path))
        img.show()
