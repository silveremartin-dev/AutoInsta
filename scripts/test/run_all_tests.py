import sys
import subprocess
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEST_DIR = BASE_DIR / "scripts" / "test"

TEST_FILES = [
    "test_pipeline.py",
    "test_emergency_deadman.py",
    "test_sensors_local.py"
]

def main():
    print("=" * 65)
    print(" [*] LANCEMENT DE LA SUITE DE TESTS COMPLÈTE AUTOINSTA")
    print("=" * 65)
    
    python_exe = sys.executable
    passed = 0
    failed = 0

    for test_file in TEST_FILES:
        script_path = TEST_DIR / test_file
        print(f"\n▶ Exécution : {test_file}...")
        res = subprocess.run([python_exe, str(script_path)])
        if res.returncode == 0:
            passed += 1
        else:
            failed += 1
            print(f"❌ ÉCHEC : {test_file} s'est terminé avec le code {res.returncode}")

    print("\n" + "=" * 65)
    print(f" RÉSULTAT GLOBAL : {passed}/{len(TEST_FILES)} tests réussis")
    if failed == 0:
        print(" 🎉 TOUS LES MODULES AUTOINSTA SONT OPÉRATIONNELS !")
    else:
        print(f" ⚠ {failed} test(s) en erreur.")
    print("=" * 65)

    sys.exit(failed)

if __name__ == "__main__":
    main()
