class A:
    def has_perm(self, num) -> bool:
        print("A")
        if num % 2 == 0:
            return False
        return True


class B:
    def has_perm(self, num) -> bool:
        print("B")
        if num % 2 == 0:
            return True
        return False


class C(B, A):
    def has_perm(self) -> bool:
        print("C")
        return True


c = C()
print(c.has_perm(1))
