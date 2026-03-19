#!/usr/bin/env bash
set -euo pipefail

DATASET="dataset_open7_500k_v2.npz"

BC_MODEL="policy_bc_open7_500k_v2.pt"
RL_MODEL="policy_rl_open7_500k_v2.pt"
RL_SHAPED_MODEL="policy_rl_shaped_open7_500k_v2.pt"
RL_SHAPED_BEST_MODEL="policy_best_shaped_open7_500k_v2.pt"

SELFPLAY_GAMES=5000
CROSSPLAY_GAMES=5000

echo "===================================="
echo "Ristiseiska experiment 500k (dataset v2)"
echo "===================================="

echo
echo "Dataset target: $DATASET"

echo
echo "1️⃣ Generating dataset (filtered decision states)"

python generate_data.py \
  --samples 500000 \
  --out "$DATASET" \
  --deal-seed 42 \
  --policy-seed 123 \
  --keep-forced-prob 0.25 \
  --interesting-multiplier 2

echo
echo "2️⃣ Training BC"

python train_bc.py \
  --data "$DATASET" \
  --epochs 5 \
  --batch 256 \
  --lr 3e-4 \
  --out "$BC_MODEL"

echo
echo "3️⃣ Training RL (neutral shaping)"

python train_reinforce.py \
  --init "$BC_MODEL" \
  --episodes 3000 \
  --max-steps 20000 \
  --deal-seed 1000 \
  --opp-seed 123 \
  --lr 3e-4 \
  --baseline-alpha 0.05 \
  --w-step 0.0 \
  --w-cont 0.0 \
  --w-play-card 0.0 \
  --eval-every 200 \
  --eval-games 300 \
  --out "$RL_MODEL"

echo
echo "4️⃣ Training shaped RL"

python train_reinforce_shaped.py \
  --init "$BC_MODEL" \
  --episodes 3000 \
  --max-steps 20000 \
  --deal-seed 1000 \
  --opp-seed 123 \
  --lr 3e-4 \
  --baseline-alpha 0.05 \
  --w-hand-delta 0.02 \
  --w-step 0.001 \
  --w-cont 0.005 \
  --w-path-delta 0.01 \
  --w-end-play 0.003 \
  --eval-every 200 \
  --eval-games 300 \
  --best-metric rank_mean \
  --out "$RL_SHAPED_MODEL" \
  --best-out "$RL_SHAPED_BEST_MODEL"

echo
echo "5️⃣ Selfplay evaluation"

echo "--- BC ---"
python evaluate_selfplay.py \
  --model "$BC_MODEL" \
  --games "$SELFPLAY_GAMES" \
  --mode argmax

echo "--- RL ---"
python evaluate_selfplay.py \
  --model "$RL_MODEL" \
  --games "$SELFPLAY_GAMES" \
  --mode argmax

echo "--- SHAPED RL (final) ---"
python evaluate_selfplay.py \
  --model "$RL_SHAPED_MODEL" \
  --games "$SELFPLAY_GAMES" \
  --mode argmax

if [ -f "$RL_SHAPED_BEST_MODEL" ]; then
  echo "--- SHAPED RL (best checkpoint) ---"
  python evaluate_selfplay.py \
    --model "$RL_SHAPED_BEST_MODEL" \
    --games "$SELFPLAY_GAMES" \
    --mode argmax
fi

echo
echo "6️⃣ Crossplay evaluation"

echo "--- RL vs SHAPED final ---"
python evaluate_crossplay.py \
  --model_a "$RL_MODEL" \
  --model_b "$RL_SHAPED_MODEL" \
  --a_seat 0 \
  --games "$CROSSPLAY_GAMES" \
  --mode argmax

echo "--- BC vs RL ---"
python evaluate_crossplay.py \
  --model_a "$BC_MODEL" \
  --model_b "$RL_MODEL" \
  --a_seat 0 \
  --games "$CROSSPLAY_GAMES" \
  --mode argmax

echo "--- BC vs SHAPED final ---"
python evaluate_crossplay.py \
  --model_a "$BC_MODEL" \
  --model_b "$RL_SHAPED_MODEL" \
  --a_seat 0 \
  --games "$CROSSPLAY_GAMES" \
  --mode argmax

if [ -f "$RL_SHAPED_BEST_MODEL" ]; then
  echo "--- RL vs SHAPED best ---"
  python evaluate_crossplay.py \
    --model_a "$RL_MODEL" \
    --model_b "$RL_SHAPED_BEST_MODEL" \
    --a_seat 0 \
    --games "$CROSSPLAY_GAMES" \
    --mode argmax

  echo "--- BC vs SHAPED best ---"
  python evaluate_crossplay.py \
    --model_a "$BC_MODEL" \
    --model_b "$RL_SHAPED_BEST_MODEL" \
    --a_seat 0 \
    --games "$CROSSPLAY_GAMES" \
    --mode argmax
fi

echo
echo "===================================="
echo "Done."
echo "Dataset:            $DATASET"
echo "BC model:           $BC_MODEL"
echo "RL model:           $RL_MODEL"
echo "Shaped final model: $RL_SHAPED_MODEL"
echo "Shaped best model:  $RL_SHAPED_BEST_MODEL"
echo "===================================="