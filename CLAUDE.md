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

## Claude documentation

The folder "claude-code-docs" contains the documentation for Claude code in .md files.

## Shopify API documentation

This folder contains the Shopify API documentation, formatted as html files.

## Shopify API credentials

The Shopify API credentials are in the .env file. The API key, secret and access token are stored there, along with the URL for Sentia Spirits' graphql API.

## Shopify API scope

This Shopify API integration has the following scopes: read_analytics, read_inventory, read_orders, read_products, read_reports. Tell me in chat if there are vital sub-processes that would be impossible without access to additional scopes.