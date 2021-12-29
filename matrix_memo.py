"Setting certain fields in blender and then reading back from them is not gaurenteed to give the same results"

from bpy.types import Object, PoseBone
from mathutils import Matrix


class MatrixMemo:
    def __init__(self, target: Object):
        self.__matrix = None
        self.target = target

    def get_matrix(self) -> Matrix:
        if self.__matrix is not None:
            return self.__matrix
        if isinstance(self.target, PoseBone):
            return self.target.matrix.copy()
        return self.target.matrix_basis.copy()

    def set_matrix(self, m: Matrix) -> Matrix:
        if isinstance(self.target, PoseBone):
            # This gets deferred until next frame or something
            self.target.matrix = m
        else:
            self.target.matrix_basis = m
        self.__matrix = m
