import os
from pickle import FALSE
import sys

# add jenkins config location to PATH
sys.path.append(os.environ['CI_SITE_CONFIG'])

import ci_site_config
import argparse
import subprocess
import shlex
import common
import re
import shutil

verbose = False
spacing='\t'

def print_results(stage_name, passes, fails, failed_tests, excludes=None,
                  excluded_tests=None):
    total = passes + fails
    # log was empty or not valid
    if not total:
        return

    percent = passes/total * 100
    print(f"{spacing}{stage_name}: ".ljust(40), end='')
    print(f"{passes}/{total}".ljust(8), end='')
    print(f"= {percent:.2f}%".ljust(12), end = '')
    print("Pass")
    if fails:
        print(f"{spacing}\tFailed tests: {fails}")
        for test in failed_tests:
                print(f'{spacing}\t\t{test}')
    if (verbose):
        if excludes:
            print(f"{spacing}\tExcluded/Notrun tests: {excludes} ")
            for test in excluded_tests:
                print(f'{spacing}\t\t{test}')

def summarize_fi_info(log_dir, prov, build_mode):
    file_name = f'{prov}_fi_info_{build_mode}'
    if not os.path.exists(f'{log_dir}/{file_name}'):
        return

    log = open(f'{log_dir}/{file_name}', 'r')
    line = log.readline()
    passes = 0
    fails = 0
    failed_tests = []
    #check if it failed
    while line:
        if "exiting with" in line:
            fails += 1
            failed_tests.append(f"fi_info {prov}")

        line = log.readline()

    if not fails:
        passes += 1

    print_results(f"{prov} fabtests {build_mode}", passes, fails, failed_tests)

    log.close()
    return int(fails)

def summarize_fabtests(log_dir, prov, build_mode=None):
    file_name = f'{prov}_fabtests_{build_mode}'
    if not os.path.exists(f'{log_dir}/{file_name}'):
        return

    log = open(f'{log_dir}/{file_name}', 'r')
    line = log.readline()
    passes = 0
    fails = 0
    excludes = 0
    failed_tests = []
    excluded_tests = []
    test_name_string='no_test'
    while line:
        # don't double count ubertest output
        if 'ubertest' in line and 'client_cmd:' in line:
            while 'name:' not in line: # skip past client output in ubertest
                line = log.readline()

        if 'name:' in line:
            test_name = line.split()[2:]
            test_name_string = ' '.join(test_name)

        if 'result:' in line:
            result_line = line.split()
            # lines can look like 'result: Pass' or
            # 'Ending test 1 result: Success'
            result = (result_line[result_line.index('result:') + 1]).lower()
            if result == 'pass' or result == 'success':
                    passes += 1

            if result == 'fail':
                fails += 1
                if 'ubertest' in test_name_string:
                    idx = (result_line.index('result:') - 1)
                    ubertest_number = int((result_line[idx].split(',')[0]))
                    failed_tests.append(f"{test_name_string}: " \
                                        f"{ubertest_number}")
                else:
                    failed_tests.append(test_name_string)

            if result == 'excluded' or result == 'notrun':
                excludes += 1
                excluded_tests.append(test_name_string)

        if "exiting with" in line:
            fails += 1
            failed_tests.append(test_name_string)

        line = log.readline()

    print_results(f"{prov} fabtests {build_mode}", passes, fails, failed_tests,
                  excludes, excluded_tests)

    log.close()
    return int(fails)

def summarize_ze(log_dir, prov, test_type, build_mode=None):
    file_name = f'ze-{prov}_{test_type}_{build_mode}'
    if not os.path.exists(f'{log_dir}/{file_name}'):
        return

    log = open(f'{log_dir}/{file_name}', 'r')
    line = log.readline()
    passes = 0
    fails = 0
    excludes = 0
    failed_tests = []
    excluded_tests = []
    test_name_string = 'no_test'
    while line:
        if 'name:' in line:
            test_name = line.split()[2:]
            test_name_string = ' '.join(test_name)

        if 'result:' in line:
            result_line = line.split()
            # lines can look like 'result: Pass' or
            # 'Ending test 1 result: Success'
            result = (result_line[result_line.index('result:') + 1]).lower()
            if result == 'pass' or result == 'success':
                    passes += 1

            if result == 'fail':
                fails += 1
                failed_tests.append(test_name_string)

            if result == 'excluded' or result == 'notrun':
                excludes += 1
                excluded_tests.append(test_name_string)

        if "exiting with" in line:
            fails += 1
            failed_tests.append(test_name_string)

        line = log.readline()

    print_results(f"ze {prov} {test_type} {build_mode}", passes, fails,
                  failed_tests, excludes, excluded_tests)

    log.close()
    return int(fails)

def summarize_oneccl(log_dir, prov, build_mode=None):
    if 'GPU' in prov:
        file_name = f'{prov}_onecclgpu_{build_mode}'
    else:
        file_name = f'{prov}_oneccl_{build_mode}'

    if not os.path.exists(f'{log_dir}/{file_name}'):
        return

    log = open(f'{log_dir}/{file_name}', 'r')
    line = log.readline()
    passes = 0
    fails = 0
    failed_tests = []
    name = 'no_test'
    while line:
        #lines look like path/run_oneccl.sh ..... -test examples ..... test_name
        if " -test" in line:
            tokens = line.split()
            name = f"{tokens[tokens.index('-test') + 1]} " \
                   f"{tokens[len(tokens) - 1]}"

        if 'PASSED' in line:
            passes += 1

        if 'FAILED' in line or "exiting with" in line:
            fails += 1
            failed_tests.append(name)

        line = log.readline()

    print_results(f"{prov} oneccl {build_mode}", passes, fails, failed_tests)

    log.close()
    return int(fails)

def summarize_shmem(log_dir, prov, build_mode=None):
    file_name = f'SHMEM_{prov}_shmem_{build_mode}'
    if not os.path.exists(f'{log_dir}/{file_name}'):
        return

    log = open(f'{log_dir}/{file_name}', 'r')
    line = log.readline()
    passes = 0
    fails = 0
    failed_tests = []
    total = 0
    if prov == 'uh':
        keyphrase = 'Summary'
        # Failed
    if prov == 'isx':
        keyphrase = 'Scaling'
        # Failed
    if prov == 'prk':
        keyphrase = 'Solution'
        # ERROR:

    name = 'no_test'
    while line:
        if prov == 'uh':
            # (test_002) Running test_shmem_atomics.x: Test all atomics... OK
            # (test_003) Running test_shmem_barrier.x: Tests barrier ... Failed
            if "Running test_" in line:
                tokens = line.split()
                for token in tokens:
                    if 'test_' in token:
                        name = token
                if tokens[len(tokens) - 1] == 'OK':
                    passes += 1
                else:
                    fails += 1
                    failed_tests.append(name)
            # Summary
            # x/z Passed.
            # y/z Failed.
            if 'Summary' in line: #double check
                passed = log.readline()
                failed = log.readline()
                if passes != int(passed.split()[1].split('/')[0]):
                    print(f"passes {passes} do not match log reported passes " \
                          f"{int(passed.split()[1].split('/')[0])}")
                if fails != int(failed.split()[1].split('/')[0]):
                    print(f"fails {fails} does not match log fails " \
                          f"{int(failed.split()[1].split('/')[0])}")

            if "exiting with" in line:
                fails += 1
                failed_tests.append(f"{prov} {passes + fails}")
        if prov == 'prk':
            if keyphrase in line:
                passes += 1
            if 'ERROR:' in line or "exiting with" in line:
                fails += 1
                failed_tests.append(f"{prov} {passes + fails}")
            if 'test(s)' in line:
                if int(line.split()[0]) != fails:
                    print(f"fails {fails} does not match log reported fails " \
                          f"{int(line.split()[0])}")
        if prov == 'isx':
            if keyphrase in line:
                passes += 1
            if 'Failed' in line or "exiting with" in line:
                fails += 1
                failed_tests.append(f"{prov} {passes + fails}")
            if 'test(s)' in line:
                if int(line.split()[0]) != fails:
                    print(f"fails {fails} does not match log reported fails " \
                          f"{int(line.split()[0])}")

        line = log.readline()

    print_results(f"shmem {prov} {build_mode}", passes, fails, failed_tests)

    log.close()
    return int(fails)

def summarize_mpichtestsuite(log_dir, prov, mpi, build_mode=None):
    file_name = f'MPICH testsuite_{prov}_{mpi}_mpichtestsuite_{build_mode}'
    if not os.path.exists(f'{log_dir}/{file_name}'):
        return

    log = open(f'{log_dir}/{file_name}', 'r')
    line = log.readline()
    passes = 0
    fails = 0
    failed_tests = []
    if mpi == 'impi':
        run = 'mpiexec'
    else:
        run = 'mpirun'

    while line:
        if run in line:
            name = line.split()[len(line.split()) - 1].split('/')[1]
            #assume pass
            passes += 1

        # Fail cases take away assumed pass
        if "exiting with" in line:
            fails += 1
            passes -= 1
            failed_tests.append(f'{name}')
            #skip to next test
            while run not in line:
                line = log.readline()
            continue

        line = log.readline()

    print_results(f"{prov} {mpi} mpichtestsuite {build_mode}", passes, fails,
                  failed_tests)

    log.close()
    return int(fails)

def summarize_imb(log_dir, prov, mpi, build_mode=None):
    file_name = f'MPI_{prov}_{mpi}_IMB_{build_mode}'
    if not os.path.exists(f'{log_dir}/{file_name}'):
        return

    log = open(f'{log_dir}/{file_name}', 'r')
    line = log.readline()
    passes = 0
    fails = 0
    failed_tests = []
    if mpi == 'impi':
        run = 'mpiexec'
    else:
        run = 'mpirun'

    while line:
        if 'part' in line:
            test_type = line.split()[len(line.split()) - 2]

        if "Benchmarking" in line:
            name = line.split()[len(line.split()) - 1]
            passes += 1

        if "exiting with" in line:
            fails += 1
            failed_tests.append(f"{test_type} {name}")
            passes -= 1

        line = log.readline()

    print_results(f"{prov} {mpi} IMB {build_mode}", passes, fails, failed_tests)

    log.close()
    return int(fails)

def summarize_osu(log_dir, prov, mpi, build_mode=None):
    file_name = f'MPI_{prov}_{mpi}_osu_{build_mode}'
    if not os.path.exists(f'{log_dir}/{file_name}'):
        return

    log = open(f'{log_dir}/{file_name}', 'r')
    line = log.readline()
    passes = 0
    fails = 0
    failed_tests = []
    if mpi == 'impi':
        run = 'mpiexec'
    else:
        run = 'mpirun'

    while line:
        if "# OSU" in line:
            tokens = line.split()
            name = " ".join(tokens[tokens.index('OSU') + 1:tokens.index('Test')])
            test_type = tokens[1]
            passes += 1

        if "exiting with" in line:
            fails += 1
            failed_tests.append(f"{test_type} {name}")
            passes -= 1

        line = log.readline()

    print_results(f"{prov} {mpi} OSU {build_mode}", passes, fails, failed_tests)

    log.close()
    return int(fails)

if __name__ == "__main__":
#read Jenkins environment variables
    # In Jenkins,  JOB_NAME  = 'ofi_libfabric/master' vs BRANCH_NAME = 'master'
    # job name is better to use to distinguish between builds of different
    # jobs but with same branch name.
    jobname = os.environ['JOB_NAME']
    buildno = os.environ['BUILD_NUMBER']
    workspace = os.environ['WORKSPACE']

    parser = argparse.ArgumentParser()
    parser.add_argument('--summary_item', help="functional test to summarize",
                         choices=['fabtests', 'imb', 'osu', 'mpichtestsuite',
                         'oneccl', 'shmem', 'ze', 'all'])
    parser.add_argument('--ofi_build_mode', help="select buildmode debug or dl",
                        choices=['dbg', 'dl', 'reg'], default='all')
    parser.add_argument('-v', help="Verbose mode. Print excluded tests", \
                        action='store_true')

    args = parser.parse_args()
    verbose = args.v

    args = parser.parse_args()
    summary_item = args.summary_item

    mpi_list = ['impi', 'mpich', 'ompi']

    if (args.ofi_build_mode):
        ofi_build_mode = args.ofi_build_mode
    else:
        ofi_build_mode = 'reg'

    log_dir = f'{ci_site_config.install_dir}/{jobname}/{buildno}/log_dir'
    ret = 0
    err = 0

    build_modes = ['reg', 'dbg', 'dl']
    for mode in build_modes:
        if ofi_build_mode != 'all' and mode != ofi_build_mode:
            continue

        print(f"Summarizing {mode} build mode:")
        if summary_item == 'fabtests' or summary_item == 'all':
            for prov,util in common.prov_list:
                if util:
                    prov = f'{prov}-{util}'

                ret = summarize_fabtests(log_dir, prov, mode)
                err += ret if ret else 0
                ret = summarize_fi_info(log_dir, prov, mode)
                err += ret if ret else 0

        if summary_item == 'mpichtestsuite' or summary_item == 'all':
            for mpi in mpi_list:
                for item in ['tcp-rxm', 'verbs-rxm', 'net']:
                    ret = summarize_imb(log_dir, item, mpi, mode)
                    err += ret if ret else 0

        if summary_item == 'osu' or summary_item == 'all':
            for mpi in mpi_list:
                    for item in ['tcp-rxm', 'verbs-rxm']:
                        ret = summarize_osu(log_dir, item, mpi, mode)
                        err += ret if ret else 0

        if summary_item == 'mpichtestsuite' or summary_item == 'all':
            for mpi in mpi_list:
                    for item in ['tcp-rxm', 'verbs-rxm', 'sockets']:
                        ret = summarize_mpichtestsuite(log_dir, item, mpi, mode)
                        err += ret if ret else 0

        if summary_item == 'oneccl' or summary_item == 'all':
            ret = summarize_oneccl(log_dir, 'oneCCL', ofi_build_mode)
            err += ret if ret else 0
            ret = summarize_oneccl(log_dir, 'oneCCL-GPU', mode)
            err += ret if ret else 0

        if summary_item == 'shmem' or summary_item == 'all':
            ret = summarize_shmem(log_dir, 'uh', mode)
            err += ret if ret else 0
            ret = summarize_shmem(log_dir, 'prk', mode)
            err += ret if ret else 0
            ret = summarize_shmem(log_dir, 'isx', mode)
            err += ret if ret else 0

        if summary_item == 'ze' or summary_item == 'all':
            test_types = ['h2d', 'd2d'] #, 'xd2d']
            for type in test_types:
                ret = summarize_ze(log_dir, 'shm', type, mode)
                err += ret if ret else 0

    exit(err)
