
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

namespace gcopter {
bool smoothedL1(const double &x,
                                   const double &mu,
                                   double &f,
                                   double &df) {
    if (x < 0.0) {
        return false;
    } else if (x > mu) {
        f = x - 0.5 * mu;
        df = 1.0;
        return true;
    } else {
        const double xdmu = x / mu;
        const double sqrxdmu = xdmu * xdmu;
        const double mumxd2 = mu - 0.5 * x;
        f = mumxd2 * sqrxdmu * xdmu;
        df = sqrxdmu * ((-0.5) * xdmu + 3.0 * mumxd2 / mu);
        return true;
    }
}
}
void expConstraints(const VecDf &T,
                                       const MatD3f &coeffs,
                                       const VecDi &hIdx,
                                       const PolyhedraH &hPolys,
                                       const std::vector<PassageFaceCandidates> &hPolyPassageCandidates,
                                       const Mat3Df &waypoint_attractor,
                                       const VecDf &waypoint_attractor_dead_d,
                                       const double &smoothFactor,
                                       const int &integralResolution,
                                       const VecDf &magnitudeBounds,
                                       const VecDf &penaltyWeights,
                                       const double &weightClr,
                                       const double &clearanceMargin,
                                       const double &clearanceSpeedGate,
                                       const double &clearanceSpeedTransition,
                                       const double &weightPassageCenter,
                                       const double &passageCenterMaxWidth,
                                       const double &passageCenterDeadband,
                                       flatness::FlatnessMap &flatMap,
        // outputs
                                       double &cost,
                                       VecDf &gradT,
                                       MatD3f &gradC,
                                       VecDf &pena_log) {
    /* 1) define some varible alias*/
    const auto &vmax = magnitudeBounds[0];
    const auto &amax = magnitudeBounds[1];
    const auto &jmax = magnitudeBounds[2];
    const auto &omgmax = magnitudeBounds[3];
    const auto &accthrmin = magnitudeBounds[4];
    const auto &accthrmax = magnitudeBounds[5];

    const auto &vmaxSqr = vmax * vmax;
    const auto &amaxSqr = amax * amax;
    const auto &jmaxSqr = jmax * jmax;
    const auto &omgmaxSqr = omgmax * omgmax;

    const auto &thrustMean = 0.5 * (accthrmax + accthrmin);
    const auto &thrustRadi = 0.5 * std::abs(accthrmax - accthrmin);
    const auto &thrustSqrRadi = thrustRadi * thrustRadi;

    const auto &weightPos = penaltyWeights[0];
    const auto &weightVel = penaltyWeights[1];
    const auto &weightAcc = penaltyWeights[2];
    const auto &weightJer = penaltyWeights[3];
    const auto &weightAtt = penaltyWeights[4];
    const auto &weightOmg = penaltyWeights[5];
    const auto &weightAccThr = penaltyWeights[6];

    const auto &piece_num = T.size();

    const bool clearance_gate_first = clearance_gate_policy::enabled();
    bool clearance_zero_gate_skipped = false;
    const double integralFrac = 1.0 / integralResolution;
    VecDf max_pena(8);
    max_pena.setZero();

    /* 2) add integral cost */

    for (int i = 0; i < piece_num; i++) {
        const Mat83f &c = coeffs.block<8, 3>(i * 8, 0);
        const auto &step = T(i) * integralFrac;
        for (int j = 0; j <= integralResolution; j++) {
            double s1 = j * step;
            double s2 = s1 * s1;
            double s3 = s2 * s1;
            double s4 = s2 * s2;
            double s5 = s4 * s1;
            double s6 = s4 * s2;
            double s7 = s4 * s3;
            Vec8f beta0, beta1, beta2, beta3, beta4;
            beta0 << 1.0, s1, s2, s3, s4, s5, s6, s7;
            beta1 << 0.0, 1.0, 2.0 * s1, 3.0 * s2, 4.0 * s3, 5.0 * s4, 6.0 * s5, 7.0 * s6;
            beta2 << 0.0, 0.0, 2.0, 6.0 * s1, 12.0 * s2, 20.0 * s3, 30.0 * s4, 42.0 * s5;
            beta3 << 0.0, 0.0, 0.0, 6.0, 24.0 * s1, 60.0 * s2, 120.0 * s3, 210.0 * s4;
            beta4 << 0.0, 0.0, 0.0, 0.0, 24.0, 120.0 * s1, 360.0 * s2, 840.0 * s3;
            //beta5 << 0.0, 0.0, 0.0, 0., 0.0, 120.0, 720.0 * s1, 2520.0 * s2;

            const Vec3f pos = c.transpose() * beta0;
            const Vec3f vel = c.transpose() * beta1;
            const Vec3f acc = c.transpose() * beta2;
            const Vec3f jer = c.transpose() * beta3;
            const Vec3f sna = c.transpose() * beta4;

            double tmp_cost{0.0};
            Vec3f gradPos{0, 0, 0}, gradVel{0, 0, 0}, gradAcc{0, 0, 0}, gradJer{0, 0, 0};

            /* 2.1  For position cost */
            const auto &L = hIdx(i);
            const auto &K = hPolys[L].rows();
            if (weightPos > 0) {
                for (int k = 0; k < K; k++) {
                    const Vec3f outerNormal = hPolys[L].block<1, 3>(k, 0);
                    const double violaPos = outerNormal.dot(pos) + hPolys[L](k, 3);
                    if (violaPos > max_pena(POS_IDX)) max_pena(POS_IDX) = violaPos;
                    double violaPosPena, violaPosPenaD;
                    if (gcopter::smoothedL1(violaPos, smoothFactor, violaPosPena, violaPosPenaD)) {
                        gradPos += weightPos * violaPosPenaD * outerNormal;
                        tmp_cost += weightPos * violaPosPena;
                    }

                }
            }
            // Use only the nearest SFC face. Summing every positive face made
            // the old cost depend on decomposition face count and could apply
            // mutually opposing gradients in narrow corridors. This remains a
            // soft corridor-centering preference, not a hard clearance claim.
            if (weightClr > 0.0 && clearanceMargin > 0.0 && K > 0) {
                double nearestViola = -std::numeric_limits<double>::infinity();
                Vec3f nearestNormal = Vec3f::Zero();
                double clearanceGate = 1.0;
                Vec3f clearanceGateGradVel = Vec3f::Zero();
                const auto compute_clearance_gate = [&]() {
                    if (clearanceSpeedGate > 0.0) {
                        const double lowSqr = clearanceSpeedGate * clearanceSpeedGate;
                        const double highSpeed = clearanceSpeedGate +
                                std::max(0.0, clearanceSpeedTransition);
                        const double highSqr = highSpeed * highSpeed;
                        const double speedSqr = vel.squaredNorm();
                        if (speedSqr >= highSqr) {
                            clearanceGate = 0.0;
                        } else if (speedSqr > lowSqr && highSqr > lowSqr) {
                            const double t = (highSqr - speedSqr) /
                                    (highSqr - lowSqr);
                            clearanceGate = t * t * (3.0 - 2.0 * t);
                            const double dGateDSpeedSqr =
                                    -6.0 * t * (1.0 - t) /
                                    (highSqr - lowSqr);
                            clearanceGateGradVel =
                                    2.0 * dGateDSpeedSqr * vel;
                        }
                    }
                };
                if (clearance_gate_first) compute_clearance_gate();
                if (!clearance_gate_first || clearanceGate > 0.0) {
                    for (int k = 0; k < K; ++k) {
                        const Vec3f outerNormal =
                                hPolys[L].block<1, 3>(k, 0);
                        const double normalNorm = outerNormal.norm();
                        if (normalNorm <= 1.0e-9) {
                            continue;
                        }
                        const double violaClr =
                                (outerNormal.dot(pos) + hPolys[L](k, 3)) /
                                normalNorm + clearanceMargin;
                        if (violaClr > nearestViola) {
                            nearestViola = violaClr;
                            nearestNormal = outerNormal / normalNorm;
                        }
                    }
                } else if (clearanceGate == 0.0) {
                    clearance_zero_gate_skipped = true;
                }
                if (!clearance_gate_first) compute_clearance_gate();
                double violaClrPena, violaClrPenaD;
                if (clearanceGate > 0.0 &&
                    gcopter::smoothedL1(nearestViola, smoothFactor,
                                        violaClrPena, violaClrPenaD)) {
                    gradPos += weightClr * clearanceGate *
                            violaClrPenaD * nearestNormal;
                    gradVel += weightClr * violaClrPena *
                            clearanceGateGradVel;
                    tmp_cost += weightClr * clearanceGate * violaClrPena;
                }
            }
            if (weightPassageCenter > 0.0 &&
                passageCenterMaxWidth > 0.0 && K > 1) {
                const auto passage = findPassageFacePair(
                        hPolys[L], hPolyPassageCandidates[L], pos,
                        passageCenterMaxWidth);
                if (passage.valid) {
                    const double absolute_imbalance =
                            std::abs(passage.imbalance_m);
                    const double excess = absolute_imbalance -
                            passageCenterDeadband;
                    if (excess > 0.0) {
                        const double direction = passage.imbalance_m >= 0.0
                                ? 1.0 : -1.0;
                        gradPos += weightPassageCenter * 2.0 * excess *
                                direction * passage.imbalance_gradient;
                        tmp_cost += weightPassageCenter * excess * excess;
                    }
                }
            }

            /* 2.2  For attract point cost  */
            if (weightAtt > 0.0) {
                const auto is_waypoint = (j == 0) && (i != 0);
                const auto is_end = ((j == integralResolution) && (i != piece_num - 1));
                const auto idx = is_end ? i : i - 1;

                if (is_waypoint || is_end) {
                    Vec3f p_a = pos - waypoint_attractor.col(idx);
                    const auto &violaAtt =
                            p_a.squaredNorm() - waypoint_attractor_dead_d(idx) * waypoint_attractor_dead_d(idx);
                    double violaAttPena, violaAttPenaD;
                    if (violaAtt > max_pena(ATT_IDX)) max_pena(ATT_IDX) = violaAtt;
                    if (gcopter::smoothedL1(violaAtt, smoothFactor, violaAttPena, violaAttPenaD)) {
                        gradPos += weightAtt * violaAttPenaD * 2.0 * p_a;
                        tmp_cost += weightAtt * violaAttPena;
                    }
                }
            }

            /* 2.3 For vel cost  */
            const auto &violaVel = vel.squaredNorm() - vmaxSqr;
            double violaVelPena, violaVelPenaD;
            if (weightVel > 0 && gcopter::smoothedL1(violaVel, smoothFactor, violaVelPena, violaVelPenaD)) {
                gradVel += weightVel * violaVelPenaD * 2.0 * vel;
                tmp_cost += weightVel * violaVelPena;
                if (violaVel > max_pena(VEL_IDX)) max_pena(VEL_IDX) = violaVel;
            }

            /* 2.4 For acc cost  */
            const auto &violaAcc = acc.squaredNorm() - amaxSqr;
            double violaAccPena, violaAccPenaD;
            if (weightAcc > 0 && gcopter::smoothedL1(violaAcc, smoothFactor, violaAccPena, violaAccPenaD)) {
                gradAcc += weightAcc * violaAccPenaD * 2.0 * acc;
                tmp_cost += weightAcc * violaAccPena;
                if (violaAcc > max_pena(ACC_IDX)) max_pena(ACC_IDX) = violaAcc;
            }

            /* 2.5 For acc cost  */
            const auto &violaJer = jer.squaredNorm() - jmaxSqr;
            double violaJerPena, violaJerPenaD;
            if (weightJer > 0 && gcopter::smoothedL1(violaJer, smoothFactor, violaJerPena, violaJerPenaD)) {
                gradJer += weightJer * violaJerPenaD * 2.0 * jer;
                tmp_cost += weightJer * violaJerPena;
                if (violaJer > max_pena(JER_IDX)) max_pena(JER_IDX) = violaJer;
            }

            Vec3f totalGradPos{0.0, 0.0, 0.0}, totalGradVel{0.0, 0.0, 0.0},
                    totalGradAcc{0.0, 0.0, 0.0}, totalGradJer{0.0, 0.0, 0.0};

            /* 2.6  For omg amd thr cost  */
            if (weightOmg > 0 && weightAccThr > 0) {
                double thr;
                Vec4f quat;
                Vec3f omg;
                flatMap.forward(vel, acc, jer, 0.0, 0.0, thr, quat, omg);
                const auto &violaOmg = omg.squaredNorm() - omgmaxSqr;
                const auto &violaThrust = (thr - thrustMean) * (thr - thrustMean) - thrustSqrRadi;

                /* 2.6.1  For omg cost  */
                double violaOmgPena, violaOmgPenaD;
                Vec3f gradOmg{0, 0, 0};
                if (weightOmg > 0 && gcopter::smoothedL1(violaOmg, smoothFactor, violaOmgPena, violaOmgPenaD)) {
                    gradOmg += weightOmg * violaOmgPenaD * 2.0 * omg;
                    tmp_cost += weightOmg * violaOmgPena;
                    if (violaOmg > max_pena(OMG_IDX)) max_pena(OMG_IDX) = violaOmg;
                }

                /* 2.6.2  For thr cost  */
                double violaThrustPena, violaThrustPenaD;
                double gradThr{0.0};
                if (weightAccThr > 0 &&
                    gcopter::smoothedL1(violaThrust, smoothFactor, violaThrustPena, violaThrustPenaD)) {
                    gradThr += weightAccThr * violaThrustPenaD * 2.0 * (thr - thrustMean);
                    tmp_cost += weightAccThr * violaThrustPena;
                    if (violaThrust > max_pena(THR_IDX)) max_pena(THR_IDX) = violaThrust;
                }
                double totalGradPsi{0.0}, totalGradPsiD{0.0};
                flatMap.backward(gradPos, gradVel, gradAcc, gradJer, gradThr, Vec4f(0, 0, 0, 0), gradOmg,
                                 totalGradPos, totalGradVel, totalGradAcc, totalGradJer,
                                 totalGradPsi, totalGradPsiD);
            } else {
                totalGradPos = gradPos;
                totalGradVel = gradVel;
                totalGradAcc = gradAcc;
                totalGradJer = gradJer;
            }

            const auto node = (j == 0 || j == integralResolution) ? 0.5 : 1.0;
            const double alpha = j * integralFrac;
            gradC.block<8, 3>(i * 8, 0) += (beta0 * totalGradPos.transpose() +
                                            beta1 * totalGradVel.transpose() +
                                            beta2 * totalGradAcc.transpose() +
                                            beta3 * totalGradJer.transpose()) *
                                           node * step;
            gradT(i) += (totalGradPos.dot(vel) +
                         totalGradVel.dot(acc) +
                         totalGradAcc.dot(jer) +
                         totalGradJer.dot(sna)) *
                        alpha * node * step +
                        node * integralFrac * tmp_cost;
            cost += node * step * tmp_cost;
        }
    }

    /* 3) log all violations */
    pena_log.tail(7) = max_pena.tail(7);
    if (clearance_zero_gate_skipped)
        clearance_gate_policy::reportSkipOnce<clearance_gate_policy::Optimizer::Exp>();
}
void backupConstraints(const Eigen::VectorXd &T,
                                          const Eigen::MatrixX3d &coeffs,
                                          const PolyhedronH &hPoly,
                                          const PassageFaceCandidates &hPolyPassageCandidates,
                                          const double &smoothFactor,
                                          const int &integralResolution,
                                          const Eigen::VectorXd &magnitudeBounds,
                                          const Eigen::VectorXd &penaltyWeights,
                                          const double &weightClr,
                                          const double &clearanceMargin,
                                          const double &clearanceSpeedGate,
                                          const double &clearanceSpeedTransition,
                                          const double &weightPassageCenter,
                                          const double &passageCenterMaxWidth,
                                          const double &passageCenterDeadband,
                                          flatness::FlatnessMap &flatMap,
                                          double &cost,
                                          Eigen::VectorXd &gradT,
                                          Eigen::MatrixX3d &gradC,
                                          VecDf &pena_log) {
//    opt_vars.magnitudeBounds
//            << cfg_.max_vel, cfg_.max_acc, cfg_.max_jerk, cfg_.max_omg, cfg_.min_acc_thr, cfg_.max_acc_thr;
//    opt_vars.penaltyWeights << cfg_.penna_pos, cfg_.penna_vel,
//            cfg_.penna_acc, cfg_.penna_jerk,
//            cfg_.penna_attract, cfg_.penna_omg,
//            cfg_.penna_thr;
    const double vmax = magnitudeBounds[0];
    const double amax = magnitudeBounds[1];
    const double jmax = magnitudeBounds[2];
    const double omgmax = magnitudeBounds[3];
    const double accthrmin = magnitudeBounds[4];
    const double accthrmax = magnitudeBounds[5];

    const double vmaxSqr = vmax * vmax;
    const double amaxSqr = amax * amax;
    const double jmaxSqr = jmax * jmax;
    const double omgmaxSqr = omgmax * omgmax;

    const double thrustMean = 0.5 * (accthrmax + accthrmin);
    const double thrustRadi = 0.5 * std::abs(accthrmax - accthrmin);
    const double thrustSqrRadi = thrustRadi * thrustRadi;

    const double weightPos = penaltyWeights[0];
    const double weightVel = penaltyWeights[1];
    const double weightAcc = penaltyWeights[2];
    const double weightJer = penaltyWeights[3];
    // const double weightAtt = penaltyWeights[4];
    const double weightOmg = penaltyWeights[5];
    const double weightAccThr = penaltyWeights[6];


    Eigen::Vector3d pos, vel, acc, jer, sna;
    Eigen::Vector3d totalGradPos, totalGradVel, totalGradAcc, totalGradJer;
    double totalGradPsi, totalGradPsiD;
    double thr;
    Eigen::Vector4d quat;
    Eigen::Vector3d omg;
    double gradThr;
    Eigen::Vector3d gradPos, gradVel, gradAcc, gradJer, gradOmg;

    double step, alpha;
    double s1, s2, s3, s4, s5, s6, s7;
    Eigen::Matrix<double, 8, 1> beta0, beta1, beta2, beta3, beta4;
    Eigen::Vector3d outerNormal;

    // Diagnostic baseline repair: disabled attitude/thrust penalties still
    // reach the max-violation log below. Never read uninitialized values there.
    // The active flatness branch overwrites both before use, as before.
    double violaPos, violaVel, violaAcc, violaJer, violaOmg{0.0}, violaThrust{0.0};
    double violaPosPenaD, violaVelPenaD, violaAccPenaD, violaJerPenaD, violaOmgPenaD, violaThrustPenaD;
    double violaPosPena, violaVelPena, violaAccPena, violaJerPena, violaOmgPena, violaThrustPena;
    double node, pena;
    const auto pieceNum = T.size();
    const bool clearance_gate_first = clearance_gate_policy::enabled();
    bool clearance_zero_gate_skipped = false;
    const double integralFrac = 1.0 / integralResolution;
    double pos_penna_log = 0.0;
    double max_pos_viola_log = 0.0;
    double vel_penna_log = 0.0;
    double max_vel_viola_log = 0.0;
    double acc_penna_log = 0.0;
    double max_acc_viola_log = 0.0;
    double jer_penna_log = 0.0;
    double max_jer_viola_log = 0.0;
    double omg_penna_log = 0.0;
    double max_omg_viola_log = 0.0;
    double thr_penna_log = 0.0;
    double max_thr_viola_log = 0.0;

    for (int i = 0; i < pieceNum; i++) {
        const Eigen::Matrix<double, 8, 3> &c = coeffs.block<8, 3>(i * 8, 0);

        step = T(i) * integralFrac;
        for (int j = 0; j <= integralResolution; j++) {
            s1 = j * step;
            s2 = s1 * s1;
            s3 = s2 * s1;
            s4 = s2 * s2;
            s5 = s4 * s1;
            s6 = s4 * s2;
            s7 = s4 * s3;
            beta0 << 1.0, s1, s2, s3, s4, s5, s6, s7;
            beta1 << 0.0, 1.0, 2.0 * s1, 3.0 * s2, 4.0 * s3, 5.0 * s4, 6.0 * s5, 7.0 * s6;
            beta2 << 0.0, 0.0, 2.0, 6.0 * s1, 12.0 * s2, 20.0 * s3, 30.0 * s4, 42.0 * s5;
            beta3 << 0.0, 0.0, 0.0, 6.0, 24.0 * s1, 60.0 * s2, 120.0 * s3, 210.0 * s4;
            beta4 << 0.0, 0.0, 0.0, 0.0, 24.0, 120.0 * s1, 360.0 * s2, 840.0 * s3;
//            beta5 << 0.0, 0.0, 0.0, 0., 0.0, 120.0, 720.0 * s1, 2520.0 * s2;
            pos = c.transpose() * beta0;
            vel = c.transpose() * beta1;
            acc = c.transpose() * beta2;
            jer = c.transpose() * beta3;
            sna = c.transpose() * beta4;

            const auto K = hPoly.rows();

            violaVel = vel.squaredNorm() - vmaxSqr;
            violaAcc = acc.squaredNorm() - amaxSqr;
            violaJer = jer.squaredNorm() - jmaxSqr;
            gradThr = 0.0;
//            gradQuat.setZero();
            gradPos << 0, 0, 0;
            gradVel << 0, 0, 0;
            gradAcc << 0, 0, 0;
            gradJer << 0, 0, 0;
            gradOmg << 0, 0, 0;
            pena = 0.0;

            if (weightPos > 0) {
                for (int k = 0; k < K; k++) {
                    outerNormal = hPoly.block<1, 3>(k, 0);
                    violaPos = outerNormal.dot(pos) + hPoly(k, 3);
                    if (gcopter::smoothedL1(violaPos, smoothFactor, violaPosPena, violaPosPenaD)) {
                        gradPos += weightPos * violaPosPenaD * outerNormal;
                        pena += weightPos * violaPosPena;
                        pos_penna_log += weightPos * violaPosPena;
                    }
                }
            }
            // Match ExpTrajOpt's face-count-independent soft preference.
            // Backup trajectories used to bypass clearance shaping entirely,
            // even though they account for many close-contact samples.
            if (weightClr > 0.0 && clearanceMargin > 0.0 && K > 0) {
                double nearestViola = -std::numeric_limits<double>::infinity();
                Eigen::Vector3d nearestNormal = Eigen::Vector3d::Zero();
                double clearanceGate = 1.0;
                Eigen::Vector3d clearanceGateGradVel =
                        Eigen::Vector3d::Zero();
                const auto compute_clearance_gate = [&]() {
                    if (clearanceSpeedGate > 0.0) {
                        const double lowSqr = clearanceSpeedGate * clearanceSpeedGate;
                        const double highSpeed = clearanceSpeedGate +
                                std::max(0.0, clearanceSpeedTransition);
                        const double highSqr = highSpeed * highSpeed;
                        const double speedSqr = vel.squaredNorm();
                        if (speedSqr >= highSqr) {
                            clearanceGate = 0.0;
                        } else if (speedSqr > lowSqr && highSqr > lowSqr) {
                            const double t = (highSqr - speedSqr) /
                                    (highSqr - lowSqr);
                            clearanceGate = t * t * (3.0 - 2.0 * t);
                            const double dGateDSpeedSqr =
                                    -6.0 * t * (1.0 - t) /
                                    (highSqr - lowSqr);
                            clearanceGateGradVel =
                                    2.0 * dGateDSpeedSqr * vel;
                        }
                    }
                };
                if (clearance_gate_first) compute_clearance_gate();
                if (!clearance_gate_first || clearanceGate > 0.0) {
                    for (int k = 0; k < K; ++k) {
                        const Eigen::Vector3d faceNormal =
                                hPoly.block<1, 3>(k, 0);
                        const double normalNorm = faceNormal.norm();
                        if (normalNorm <= 1.0e-9) {
                            continue;
                        }
                        const double violaClr =
                                (faceNormal.dot(pos) + hPoly(k, 3)) /
                                normalNorm + clearanceMargin;
                        if (violaClr > nearestViola) {
                            nearestViola = violaClr;
                            nearestNormal = faceNormal / normalNorm;
                        }
                    }
                } else if (clearanceGate == 0.0) {
                    clearance_zero_gate_skipped = true;
                }
                if (!clearance_gate_first) compute_clearance_gate();
                double violaClrPena, violaClrPenaD;
                if (clearanceGate > 0.0 &&
                    gcopter::smoothedL1(nearestViola, smoothFactor,
                                        violaClrPena, violaClrPenaD)) {
                    gradPos += weightClr * clearanceGate *
                            violaClrPenaD * nearestNormal;
                    gradVel += weightClr * violaClrPena *
                            clearanceGateGradVel;
                    pena += weightClr * clearanceGate * violaClrPena;
                }
            }
            if (weightPassageCenter > 0.0 &&
                passageCenterMaxWidth > 0.0 && K > 1) {
                const auto passage = findPassageFacePair(
                        hPoly, hPolyPassageCandidates, pos,
                        passageCenterMaxWidth);
                if (passage.valid) {
                    const double absolute_imbalance =
                            std::abs(passage.imbalance_m);
                    const double excess = absolute_imbalance -
                            passageCenterDeadband;
                    if (excess > 0.0) {
                        const double direction = passage.imbalance_m >= 0.0
                                ? 1.0 : -1.0;
                        gradPos += weightPassageCenter * 2.0 * excess *
                                direction * passage.imbalance_gradient;
                        pena += weightPassageCenter * excess * excess;
                    }
                }
            }

            if (weightVel > 0 && gcopter::smoothedL1(violaVel, smoothFactor, violaVelPena, violaVelPenaD)) {
                gradVel += weightVel * violaVelPenaD * 2.0 * vel;
                pena += weightVel * violaVelPena;
                vel_penna_log += weightVel * violaVelPena;
            }

            if (weightAcc > 0 && gcopter::smoothedL1(violaAcc, smoothFactor, violaAccPena, violaAccPenaD)) {
                gradAcc += weightAcc * violaAccPenaD * 2.0 * acc;
                pena += weightAcc * violaAccPena;
                acc_penna_log += weightAcc * violaAccPena;
            }

            if (weightJer > 0 && gcopter::smoothedL1(violaJer, smoothFactor, violaJerPena, violaJerPenaD)) {
                gradJer += weightJer * violaJerPenaD * 2.0 * jer;
                pena += weightJer * violaJerPena;
                jer_penna_log += weightJer * violaJerPena;
            }

            if (weightOmg > 0 && weightAccThr > 0) {
                flatMap.forward(vel, acc, jer, 0.0, 0.0, thr, quat, omg);
                violaOmg = omg.squaredNorm() - omgmaxSqr;
                violaThrust = (thr - thrustMean) * (thr - thrustMean) - thrustSqrRadi;

                if (gcopter::smoothedL1(violaOmg, smoothFactor, violaOmgPena, violaOmgPenaD)) {
                    gradOmg += weightOmg * violaOmgPenaD * 2.0 * omg;
                    pena += weightOmg * violaOmgPena;
                    omg_penna_log += weightOmg * violaOmgPena;
                }

                if (gcopter::smoothedL1(violaThrust, smoothFactor, violaThrustPena, violaThrustPenaD)) {
                    gradThr += weightAccThr * violaThrustPenaD * 2.0 * (thr - thrustMean);
                    pena += weightAccThr * violaThrustPena;
                    thr_penna_log += weightAccThr * violaThrustPena;
                }

//            if (smoothedL1(violaTheta, smoothFactor, violaThetaPena, violaThetaPenaD))
//            {
//                gradQuat += weightTheta * violaThetaPenaD /
//                            sqrt(1.0 - cos_theta * cos_theta) * 4.0 *
//                            Eigen::Vector4d(0.0, quat(1), quat(2), 0.0);
//                pena += weightTheta * violaThetaPena;
//            }


                flatMap.backward(gradPos, gradVel, gradAcc, gradJer, gradThr, Vec4f(0, 0, 0, 0), gradOmg,
                                 totalGradPos, totalGradVel, totalGradAcc, totalGradJer,
                                 totalGradPsi, totalGradPsiD);

            } else {
                totalGradPos = gradPos;
                totalGradVel = gradVel;
                totalGradAcc = gradAcc;
                totalGradJer = gradJer;
            }

            {
                // log the max violation
                if (violaVel > max_vel_viola_log) max_vel_viola_log = violaVel;
                if (violaAcc > max_acc_viola_log) max_acc_viola_log = violaAcc;
                if (violaJer > max_jer_viola_log) max_jer_viola_log = violaJer;
                if (violaOmg > max_omg_viola_log) max_omg_viola_log = violaOmg;
                if (violaThrust > max_thr_viola_log) max_thr_viola_log = violaThrust;
            }

            node = (j == 0 || j == integralResolution) ? 0.5 : 1.0;
            alpha = j * integralFrac;
            gradC.block<8, 3>(i * 8, 0) += (beta0 * totalGradPos.transpose() +
                                            beta1 * totalGradVel.transpose() +
                                            beta2 * totalGradAcc.transpose() +
                                            beta3 * totalGradJer.transpose()) *
                                           node * step;
            gradT(i) += (totalGradPos.dot(vel) +
                         totalGradVel.dot(acc) +
                         totalGradAcc.dot(jer) +
                         totalGradJer.dot(sna)) *
                        alpha * node * step +
                        node * integralFrac * pena;
            cost += node * step * pena;
        }
    }

//    pena_log(1) = pos_penna_log;
//    pena_log(2) = vel_penna_log;
//    pena_log(3) = acc_penna_log;
//    pena_log(4) = jer_penna_log;
//    pena_log(5) = att_penna_log;
//    pena_log(6) = omg_penna_log;
//    pena_log(7) = thr_penna_log;
    pena_log(1) = max_pos_viola_log;
    pena_log(2) = max_vel_viola_log;
    pena_log(3) = max_acc_viola_log;
    pena_log(4) = max_jer_viola_log;
    pena_log(5) = 0.0;
    pena_log(6) = max_omg_viola_log;
    pena_log(7) = max_thr_viola_log;
    if (clearance_zero_gate_skipped)
        clearance_gate_policy::reportSkipOnce<clearance_gate_policy::Optimizer::Backup>();
}
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
