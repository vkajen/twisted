# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.persisted.styles}.
"""

from __future__ import print_function, division, absolute_import

import pickle
import StringIO

from twisted.trial import unittest
from twisted.persisted.styles import (
    Versioned, Ephemeral, doUpgrade, unpickleMethod, _aybabtu)


class Foo:
    """
    Helper class.
    """
    def method(self):
        """
        Helper method.
        """



class Bar:
    """
    Helper class.
    """



class UnpickleMethodTestCase(unittest.TestCase):
    """
    Tests for the unpickleMethod function.
    """

    def test_instanceBuildingNamePresent(self):
        """
        L{unpickleMethod} returns an instance method bound to the
        instance passed to it.
        """
        foo = Foo()
        m = unpickleMethod('method', foo, Foo)
        self.assertEqual(m, foo.method)
        self.assertNotIdentical(m, foo.method)


    def test_instanceBuildingNameNotPresent(self):
        """
        If the named method is not present in the class,
        L{unpickleMethod} finds a method on the class of the instance
        and returns a bound method from there.
        """
        foo = Foo()
        m = unpickleMethod('method', foo, Bar)
        self.assertEqual(m, foo.method)
        self.assertNotIdentical(m, foo.method)



class VersionTestCase(unittest.TestCase):
    """
    Tests for L{Versioned}.
    """
    def testNullVersionUpgrade(self):
        global NullVersioned
        class NullVersioned:
            ok = 0
        pkcl = pickle.dumps(NullVersioned())
        class NullVersioned(Versioned):
            persistenceVersion = 1
            def upgradeToVersion1(self):
                self.ok = 1
        mnv = pickle.loads(pkcl)
        doUpgrade()
        assert mnv.ok, "initial upgrade not run!"

    def testVersionUpgrade(self):
        global MyVersioned
        class MyVersioned(Versioned):
            persistenceVersion = 2
            persistenceForgets = ['garbagedata']
            v3 = 0
            v4 = 0

            def __init__(self):
                self.somedata = 'xxx'
                self.garbagedata = lambda q: 'cant persist'

            def upgradeToVersion3(self):
                self.v3 += 1

            def upgradeToVersion4(self):
                self.v4 += 1
        mv = MyVersioned()
        assert not (mv.v3 or mv.v4), "hasn't been upgraded yet"
        pickl = pickle.dumps(mv)
        MyVersioned.persistenceVersion = 4
        obj = pickle.loads(pickl)
        doUpgrade()
        assert obj.v3, "didn't do version 3 upgrade"
        assert obj.v4, "didn't do version 4 upgrade"
        pickl = pickle.dumps(obj)
        obj = pickle.loads(pickl)
        doUpgrade()
        assert obj.v3 == 1, "upgraded unnecessarily"
        assert obj.v4 == 1, "upgraded unnecessarily"

    def testNonIdentityHash(self):
        global ClassWithCustomHash
        class ClassWithCustomHash(Versioned):
            def __init__(self, unique, hash):
                self.unique = unique
                self.hash = hash
            def __hash__(self):
                return self.hash

        v1 = ClassWithCustomHash('v1', 0)
        v2 = ClassWithCustomHash('v2', 0)

        pkl = pickle.dumps((v1, v2))
        del v1, v2
        ClassWithCustomHash.persistenceVersion = 1
        ClassWithCustomHash.upgradeToVersion1 = lambda self: setattr(self, 'upgraded', True)
        v1, v2 = pickle.loads(pkl)
        doUpgrade()
        self.assertEqual(v1.unique, 'v1')
        self.assertEqual(v2.unique, 'v2')
        self.failUnless(v1.upgraded)
        self.failUnless(v2.upgraded)

    def testUpgradeDeserializesObjectsRequiringUpgrade(self):
        global ToyClassA, ToyClassB
        class ToyClassA(Versioned):
            pass
        class ToyClassB(Versioned):
            pass
        x = ToyClassA()
        y = ToyClassB()
        pklA, pklB = pickle.dumps(x), pickle.dumps(y)
        del x, y
        ToyClassA.persistenceVersion = 1
        def upgradeToVersion1(self):
            self.y = pickle.loads(pklB)
            doUpgrade()
        ToyClassA.upgradeToVersion1 = upgradeToVersion1
        ToyClassB.persistenceVersion = 1
        ToyClassB.upgradeToVersion1 = lambda self: setattr(self, 'upgraded', True)

        x = pickle.loads(pklA)
        doUpgrade()
        self.failUnless(x.y.upgraded)



class VersionedSubClass(Versioned):
    pass



class SecondVersionedSubClass(Versioned):
    pass



class VersionedSubSubClass(VersionedSubClass):
    pass



class VersionedDiamondSubClass(VersionedSubSubClass, SecondVersionedSubClass):
    pass



class AybabtuTests(unittest.TestCase):
    """
    L{_aybabtu} gets all of classes in the inheritance hierarchy of its
    argument that are strictly between L{Versioned} and the class itself.
    """

    def test_aybabtuStrictEmpty(self):
        """
        L{_aybabtu} of L{Versioned} itself is an empty list.
        """
        self.assertEqual(_aybabtu(Versioned), [])


    def test_aybabtuStrictSubclass(self):
        """
        There are no classes I{between} L{VersionedSubClass} and L{Versioned},
        so L{_aybabtu} returns an empty list.
        """
        self.assertEqual(_aybabtu(VersionedSubClass), [])


    def test_aybabtuSubsubclass(self):
        """
        With a sub-sub-class of L{Versioned}, L{_aybabtu} returns a list
        containing the intervening subclass.
        """
        self.assertEqual(_aybabtu(VersionedSubSubClass),
                         [VersionedSubClass])


    def test_aybabtuStrict(self):
        """
        For a diamond-shaped inheritance graph, L{_aybabtu} returns a
        list containing I{both} intermediate subclasses.
        """
        self.assertEqual(
            _aybabtu(VersionedDiamondSubClass),
            [VersionedSubSubClass, VersionedSubClass, SecondVersionedSubClass])



class MyEphemeral(Ephemeral):

    def __init__(self, x):
        self.x = x


class EphemeralTestCase(unittest.TestCase):

    def testEphemeral(self):
        o = MyEphemeral(3)
        self.assertEqual(o.__class__, MyEphemeral)
        self.assertEqual(o.x, 3)

        pickl = pickle.dumps(o)
        o = pickle.loads(pickl)

        self.assertEqual(o.__class__, Ephemeral)
        self.assert_(not hasattr(o, 'x'))


class Pickleable:

    def __init__(self, x):
        self.x = x

    def getX(self):
        return self.x

class PicklingTestCase(unittest.TestCase):
    """Test pickling of extra object types."""

    def testModule(self):
        pickl = pickle.dumps(unittest)
        o = pickle.loads(pickl)
        self.assertEqual(o, unittest)

    def testClassMethod(self):
        pickl = pickle.dumps(Pickleable.getX)
        o = pickle.loads(pickl)
        self.assertEqual(o, Pickleable.getX)

    def testInstanceMethod(self):
        obj = Pickleable(4)
        pickl = pickle.dumps(obj.getX)
        o = pickle.loads(pickl)
        self.assertEqual(o(), 4)
        self.assertEqual(type(o), type(obj.getX))

    def testStringIO(self):
        f = StringIO.StringIO()
        f.write("abc")
        pickl = pickle.dumps(f)
        o = pickle.loads(pickl)
        self.assertEqual(type(o), type(f))
        self.assertEqual(f.getvalue(), "abc")
