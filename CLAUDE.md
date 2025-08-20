# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a manufacturing schedule MVP for an AI logistics system. The repository is in its early stages with minimal code structure - currently containing primarily data files for a manufacturing/inventory system.

## Data Architecture

The project works with manufacturing and inventory data from several key files:

- `Stock-on-hand.csv` - Product inventory data including product codes, descriptions, groups, allocated quantities, and on-hand quantities
- `Past-sales.csv` - Historical sales data for forecasting and planning
- `Red-ingredients-edited.csv`, `Black-ingredients-edited.csv`, `Gold-ingredients-edited.csv` - Ingredient compositions and costs for each product variant
- `Ingredient-lead-times.csv` - Lead times and minimum order quantities for each ingredient

## Database Configuration

- Uses PostgreSQL (Neon) as the primary database
- Database connection configured via `.env` file with `DATABASE_URL`
- Connection string format: `postgresql://user:password@host/database`

