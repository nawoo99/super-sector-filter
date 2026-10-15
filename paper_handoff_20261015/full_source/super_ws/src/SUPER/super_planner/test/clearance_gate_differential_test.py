#!/usr/bin/env python3
"""Extract real production constraints, compile outside the tree, compare OFF/ON.

No ROS, simulator, solve-tolerance changes, or copied substitute cost model.
Historical Backup undefined diagnostic values are NOT an equivalence baseline:
the separately authorized zero initialization is checked before comparison.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile


PREAMBLE = r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <vector>
#include <utils/header/eigen_alias.hpp>
#include <utils/geometry/quadrotor_flatness.hpp>
#include <traj_opt/passage_centering.hpp>
#include <traj_opt/clearance_gate_policy.hpp>
using namespace super_utils;
using namespace traj_opt;
using Vec8f = Eigen::Matrix<double, 8, 1>;
using Mat83f = Eigen::Matrix<double, 8, 3>;
#define POS_IDX 1
#define VEL_IDX 2
#define ACC_IDX 3
#define JER_IDX 4
#define ATT_IDX 5
#define OMG_IDX 6
#define THR_IDX 7
'''

CORPUS = r'''
void emit(double value) {
    std::cout.write(reinterpret_cast<const char*>(&value), sizeof(value));
}
template<typename Derived>
void emitMatrix(const Eigen::MatrixBase<Derived>& values) {
    for (Eigen::Index c = 0; c < values.cols(); ++c)
        for (Eigen::Index r = 0; r < values.rows(); ++r) emit(values(r, c));
}
int main(int argc, char** argv) {
    try {
        const bool policy = clearance_gate_policy::enabled();
        if (argc > 1 && std::string(argv[1]) == "--policy") {
            std::cout << int(policy) << '\n';
            return 0;
        }
        if (argc > 1 && std::string(argv[1]) == "--cached-policy") {
            setenv("SUPER_OPT_CLEARANCE_GATE_FIRST", policy ? "0" : "1", 1);
            if (clearance_gate_policy::enabled() != policy)
                throw std::runtime_error("policy changed after first parse");
            return 0;
        }
        const bool diagnostic_only = argc > 1 && std::string(argv[1]) == "--diagnostic-baseline";
        std::mt19937_64 rng(20260916);
        std::uniform_real_distribution<double> unit(-1.0, 1.0);
        unsigned diagnostic_checks = 0, cases = 0;
        const double inf = std::numeric_limits<double>::infinity();
        const double nan = std::numeric_limits<double>::quiet_NaN();
        const double speeds[] = {0.0, 1.0, std::nextafter(1.5, 0.0), 1.5,
            std::nextafter(1.5, inf), 1.75, std::nextafter(2.0, 0.0), 2.0,
            std::nextafter(2.0, inf), 7.0, -2.0, -7.0};
        for (unsigned id = 0; id < 896; ++id) {
            const int pieces = 1 + id % 4;
            const int resolution = id % 3 == 0 ? 1 : id % 3 == 1 ? 12 : 15;
            VecDf times(pieces);
            for (int i = 0; i < pieces; ++i) times(i) = 0.15 + 0.25 * (i + 1);
            MatD3f coeffs(8 * pieces, 3);
            coeffs.setZero();
            for (int i = 0; i < pieces; ++i) {
                coeffs.row(8 * i) << .2 * i, .3 * unit(rng), 1.0;
                coeffs(8 * i + 1, 0) = speeds[id % 12];
                if (id >= 192 && id < 768) {
                    for (int power = 1; power < 8; ++power)
                        for (int axis = 0; axis < 3; ++axis)
                            coeffs(8 * i + power, axis) += .08 * unit(rng);
                }
            }
            const int faces = 6 + (id % 5) * 6;
            PolyhedronH poly(faces, 4);
            poly.topRows(6) << 1,0,0,-2, -1,0,0,-2,
                              0,1,0,-1, 0,-1,0,-1,
                              0,0,1,-3, 0,0,-1,0;
            for (int k = 6; k < faces; ++k)
                poly.row(k) << unit(rng), unit(rng), unit(rng), -1.2;
            if (id % 19 == 0) poly.row(0).head<3>().setZero();
            if (id % 23 == 0) poly.row(1).head<3>() *= 1.e-12;
            if (id % 29 == 0) poly.row(2).head<3>() *= 1.e-9;
            if (id % 31 == 0) poly.row(3).head<3>() *= std::nextafter(1.e-9, inf);
            double weight_clr = id % 17 == 0 ? 0.0 : 1.e6;
            double margin = id % 13 == 0 ? 0.0 : .1;
            double gate = id % 7 == 0 ? 0.0 : 1.5;
            double transition = id % 11 == 0 ? 0.0 : id % 11 == 1 ? -.5 : .5;
            double passage_weight = id % 3 == 0 ? 10.0 : 0.0;
            if (id >= 768) {
                switch (id % 10) {
                    case 0: coeffs(1, 0) = nan; break;
                    case 1: coeffs(1, 0) = inf; break;
                    case 2: coeffs(0, 1) = nan; break;
                    case 3: poly(0, 0) = nan; break;
                    case 4: poly(0, 0) = inf; break;
                    case 5: poly(0, 3) = inf; break;
                    case 6: gate = nan; break;
                    case 7: gate = inf; break;
                    case 8: transition = nan; break;
                    case 9: transition = inf; break;
                }
            }
            PolyhedraH polytopes{poly, poly};
            std::vector<uint8_t> flags(faces, 1);
            auto candidates = buildPassageFaceCandidates(poly, flags, .9, .8);
            std::vector<PassageFaceCandidates> candidate_sets{candidates, candidates};
            VecDi indices(pieces);
            for (int i = 0; i < pieces; ++i) indices(i) = i % 2;
            Mat3Df attractors(3, std::max(0, pieces - 1));
            attractors.setConstant(.2);
            VecDf dead(std::max(0, pieces - 1)); dead.setConstant(.1);
            VecDf bounds(6); bounds << 7, 10, 60, 2, 3, 20;
            VecDf weights(7);
            const bool flatness_active = id % 4 == 0;
            const double omg_weight = id % 4 == 0 || id % 4 == 2 ? 100.0 : -1.0;
            const double thr_weight = id % 4 == 0 || id % 4 == 3 ? 100.0 : -1.0;
            weights << 5.e9, 5.e8, 5.e8, -5.e8, 5.e8,
                       omg_weight, thr_weight;
            if (id % 37 == 0) weights(0) = 0.0;
            for (int optimizer = 0; optimizer < 2; ++optimizer) {
                flatness::FlatnessMap flat;
                flat.reset(1.0, 9.81, .7, .8, .01, .0001);
                double cost = .375;
                VecDf grad_t = VecDf::Constant(pieces, .125);
                MatD3f grad_c = MatD3f::Constant(8 * pieces, 3, -.25);
                VecDf log = VecDf::Constant(8, -7.0);
                if (optimizer == 0)
                    expConstraints(times, coeffs, indices, polytopes, candidate_sets,
                        attractors, dead, .01, resolution, bounds, weights,
                        weight_clr, margin, gate, transition, passage_weight, 4.0, .15,
                        flat, cost, grad_t, grad_c, log);
                else
                    backupConstraints(times, coeffs, poly, candidates, .01, resolution,
                        bounds, weights, weight_clr, margin, gate, transition,
                        passage_weight, 4.0, .15, flat, cost, grad_t, grad_c, log);
                if (optimizer == 1 && !flatness_active) {
                    if (log(6) != 0.0 || log(7) != 0.0)
                        throw std::runtime_error("separate diagnostic baseline initialization failed");
                    ++diagnostic_checks;
                }
                if (!diagnostic_only) {
                    emit(id); emit(optimizer); emit(cost);
                    emitMatrix(grad_t); emitMatrix(grad_c); emitMatrix(log);
                }
                ++cases;
            }
        }
        std::cerr << "CORPUS cases=" << cases << " disabled_diagnostic_checks="
                  << diagnostic_checks << " historical_undefined_logs_not_baseline=1\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 2;
    }
}
'''


def extract(text, signature):
    begin = text.index(signature)
    masked = re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"',
                    lambda match: ' ' * len(match.group()), text, flags=re.S)
    brace = masked.index('{', begin)
    depth = 1
    end = brace + 1
    while depth:
        depth += (masked[end] == '{') - (masked[end] == '}')
        end += 1
    return text[begin:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--cxx', default='g++')
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    package = Path(__file__).resolve().parents[1]
    if args.out_dir.exists():
        raise SystemExit('refusing to overwrite an earlier attempt')
    args.out_dir.mkdir(parents=True)
    result = dict(valid=False, historical_undefined_logs_not_baseline=True,
                  diagnostic_baseline_repair='Backup violaOmg/violaThrust initialized to zero',
                  production_sources={}, sanitize=args.sanitize)
    generated = Path(tempfile.mkdtemp(prefix='super-clearance-gate-test.'))
    result['build_directory'] = str(generated)
    try:
        functions = []
        for optimizer, function in (('exp', 'expConstraints'), ('backup', 'backupConstraints')):
            path = package / 'src/traj_opt' / (optimizer + '_traj_optimizer_s4.cpp')
            source = path.read_text()
            class_name = 'ExpTrajOpt' if optimizer == 'exp' else 'BackupTrajOpt'
            body = extract(source, 'void ' + class_name + '::constraintsFunctional(')
            result['production_sources'][str(path)] = hashlib.sha256(source.encode()).hexdigest()
            result[optimizer + '_extracted_sha256'] = hashlib.sha256(body.encode()).hexdigest()
            functions.append(body.replace(class_name + '::constraintsFunctional', function, 1))
        utility_path = package / 'src/utils/optimization_utils.cpp'
        smoothed = extract(utility_path.read_text(), 'bool Gcopter<EIGENVEC>::smoothedL1(')
        smoothed = smoothed.replace('Gcopter<EIGENVEC>::smoothedL1', 'smoothedL1', 1)
        translation_unit = PREAMBLE + '\nnamespace gcopter {\n' + smoothed + '\n}\n'
        translation_unit += '\n'.join(functions) + CORPUS
        source_path = generated / 'corpus.cpp'
        source_path.write_text(translation_unit)
        (args.out_dir / 'extracted_translation_unit.cpp').write_text(translation_unit)
        binary = generated / 'corpus'
        command = [args.cxx, '-std=c++17', '-O3', '-Wall', '-Wextra',
                   '-I' + str(package / 'include'), '-I/usr/include/eigen3',
                   str(source_path), '-o', str(binary)]
        if args.sanitize:
            command[2:3] = ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        result['compile_command'] = command
        with (args.out_dir / 'compile.log').open('w') as log:
            completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=180)
        result['compile_exit'] = completed.returncode
        if completed.returncode:
            raise RuntimeError('corpus compile failed')

        def run(label, flag, argv=(), expected=0):
            env = dict(os.environ)
            if flag is None:
                env.pop('SUPER_OPT_CLEARANCE_GATE_FIRST', None)
            else:
                env['SUPER_OPT_CLEARANCE_GATE_FIRST'] = flag
            proc = subprocess.run([str(binary), *argv], env=env, capture_output=True, timeout=30)
            (args.out_dir / (label + '.stdout')).write_bytes(proc.stdout)
            (args.out_dir / (label + '.stderr')).write_bytes(proc.stderr)
            if proc.returncode != expected:
                raise RuntimeError(label + ' unexpected exit ' + str(proc.returncode))
            return proc

        for number, flag in enumerate((None, '', '0', '1')):
            proc = run('parser_valid_' + str(number), flag, ('--policy',))
            if proc.stdout != (b'1\n' if flag == '1' else b'0\n'):
                raise RuntimeError('wrong default/strict flag value')
            run('cache_once_' + str(number), flag, ('--cached-policy',))
        for number, flag in enumerate(('true', 'false', '01', ' 1', '1 ', '-1', '2')):
            run('parser_invalid_' + str(number), flag, ('--policy',), expected=2)
        baseline = run('diagnostic_baseline_off', '0', ('--diagnostic-baseline',))
        if b'disabled_diagnostic_checks=672' not in baseline.stderr:
            raise RuntimeError('missing separate diagnostic baseline coverage')
        off = run('corpus_off', '0')
        on = run('corpus_on', '1')
        if len(off.stdout) != len(on.stdout) or len(off.stdout) % 8:
            raise RuntimeError('corpus output layout mismatch')
        nan_pairs = 0
        for offset in range(0, len(off.stdout), 8):
            a, b = off.stdout[offset:offset+8], on.stdout[offset:offset+8]
            av, bv = struct.unpack('=d', a)[0], struct.unpack('=d', b)[0]
            if math.isnan(av) and math.isnan(bv):
                nan_pairs += 1  # Same nonfinite class; NaN payload bits are not a promise.
            elif a != b:
                raise RuntimeError(f'cost/gradient/log bit mismatch at double {offset//8}: {av} vs {bv}')
        for optimizer in ('exp', 'backup'):
            marker = f'[OPT_CLEARANCE_GATE_SKIP] optimizer={optimizer} gate=0'.encode()
            if marker in off.stderr or on.stderr.count(marker) != 1:
                raise RuntimeError('wrong actual-skip one-time marker behavior')
        result.update(valid=True, evaluations_per_arm=1792, finite_input_cases=768,
                      nonfinite_input_cases=128, disabled_diagnostic_baseline_checks=672,
                      mixed_attitude_thrust_weights_covered=True,
                      compared_doubles=len(off.stdout)//8, nan_class_pairs=nan_pairs,
                      finite_and_infinite_outputs_bitwise_equal=True, all_penalty_logs_compared=True,
                      policy_parser_and_cache_checked=True, actual_skip_markers_checked=True,
                      off_sha256=hashlib.sha256(off.stdout).hexdigest(),
                      on_sha256=hashlib.sha256(on.stdout).hexdigest())
    except Exception as error:
        result['error'] = str(error)
    (args.out_dir / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
