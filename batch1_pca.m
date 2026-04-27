%% Batch 1 PCA figure generation script
% Creates only the main figures required for the thesis PCA section:
%   1. Scree plot
%   2. PC1/PC2 loading bar chart
%   3. AI lap-time PCA score plot
%   4. Manual lap-time PCA score plot
%   5. AI vs manual lap-time overlay
%   6. AI sector-time correlation heatmap using whitejet
%   7. Manual sector-time correlation heatmap using whitejet
%
% Required input files in the current MATLAB folder:
%   - configs.xlsx
%   - batch1_ai_summary.csv
%   - batch1_manual_summary.csv
%
% Outputs are saved to: batch1_pca_figures_whitejet_outputs

clear; clc; close all;

%% -----------------------------
%% User settings
batchLabel = 'Batch 1';
configSheet = 1;
aiFile = 'batch1_ai_summary.csv';
manualFile = 'batch1_manual_summary.csv';
outFolder = fullfile(pwd, 'batch1_pca_figures_whitejet_outputs');

if ~exist(outFolder, 'dir')
    mkdir(outFolder);
end

%% -----------------------------
%% Load setup table
CfgAll = readtable('configs.xlsx', 'Sheet', configSheet, 'VariableNamingRule', 'preserve');

setupVars = {'suspension rear', ...
             'suspension front', ...
             'damping rear', ...
             'damping front', ...
             'motor torque', ...
             'sway front', ...
             'sway rear', ...
             'brake rear', ...
             'brake front'};

requiredCfgCols = [{'config_id'}, setupVars];
CfgAll = CfgAll(:, requiredCfgCols);

%% -----------------------------
%% Load AI and manual result tables
AI  = readtable(aiFile,     'VariableNamingRule', 'preserve');
MAN = readtable(manualFile, 'VariableNamingRule', 'preserve');

AI  = standardiseConfigColumn(AI);
MAN = standardiseConfigColumn(MAN);
CfgAll.config_id = cellstr(string(CfgAll.config_id));

%% -----------------------------
%% Keep only configs that are present in the result files
batchIDs = unique([AI.config_id; MAN.config_id]);
Cfg = CfgAll(ismember(CfgAll.config_id, batchIDs), :);

%% -----------------------------
%% Merge setup values with AI/manual outcomes
TAI  = innerjoin(Cfg, AI,  'Keys', 'config_id');
TMAN = innerjoin(Cfg, MAN, 'Keys', 'config_id');

%% -----------------------------
%% PCA on setup variables only
X = Cfg{:, setupVars};
Z = zscore(X);

[coeff, score, latent, tsquared, explained] = pca(Z); %#ok<ASGLU>

scoreTable = table(Cfg.config_id, score(:,1), score(:,2), score(:,3), ...
    'VariableNames', {'config_id','PC1','PC2','PC3'});

TAI  = innerjoin(scoreTable, TAI,  'Keys', 'config_id');
TMAN = innerjoin(scoreTable, TMAN, 'Keys', 'config_id');

%% -----------------------------
%% Display PCA variance information
explainedTable = table((1:numel(explained))', explained, cumsum(explained), ...
    'VariableNames', {'PC','ExplainedVariance_percent','CumulativeVariance_percent'});

disp([batchLabel ' - Explained variance by component (%):']);
disp(explainedTable);

%% -----------------------------
%% Figure 1: Scree plot
f1 = figure('Color','w');
pareto(explained);
xlabel('Principal Component');
ylabel('Variance Explained (%)');
title([batchLabel ' Setup PCA - Scree Plot']);
grid on;
saveFigure(f1, outFolder, '01_scree_plot');

%% -----------------------------
%% Figure 2: PC1/PC2 loadings bar chart
f2 = figure('Color','w', 'Position', [100 100 950 650]);

tiledlayout(2,1, 'TileSpacing', 'compact', 'Padding', 'compact');

nexttile;
bar(coeff(:,1));
set(gca, 'XTick', 1:numel(setupVars), ...
         'XTickLabel', setupVars, ...
         'XTickLabelRotation', 35, ...
         'TickLabelInterpreter', 'none');
ylabel('Loading');
title(sprintf('PC1 Loadings (%.1f%% variance explained)', explained(1)));
yline(0, 'k-');
grid on;

nexttile;
bar(coeff(:,2));
set(gca, 'XTick', 1:numel(setupVars), ...
         'XTickLabel', setupVars, ...
         'XTickLabelRotation', 35, ...
         'TickLabelInterpreter', 'none');
ylabel('Loading');
title(sprintf('PC2 Loadings (%.1f%% variance explained)', explained(2)));
yline(0, 'k-');
grid on;

saveFigure(f2, outFolder, '02_loadings_bar_chart');

%% -----------------------------
%% Figure 3: AI lap-time PCA scores
f3 = figure('Color','w');
scatter(TAI.PC1, TAI.PC2, 120, TAI.Lap_Time_s, 'filled');
colormap(whitejet(256));
cb = colorbar;
cb.Label.String = 'AI Lap Time (s)';
xlabel(sprintf('PC1 (%.1f%%)', explained(1)));
ylabel(sprintf('PC2 (%.1f%%)', explained(2)));
title([batchLabel ' Setup PCA - AI Lap Time Scores']);
grid on; hold on;
for i = 1:height(TAI)
    text(TAI.PC1(i)+0.03, TAI.PC2(i), TAI.config_id{i}, 'FontSize', 9, 'Interpreter', 'none');
end
saveFigure(f3, outFolder, '03_ai_lap_time_scores');

%% -----------------------------
%% Figure 4: Manual lap-time PCA scores
f4 = figure('Color','w');
scatter(TMAN.PC1, TMAN.PC2, 120, TMAN.Lap_Time_s, 'filled');
colormap(whitejet(256));
cb = colorbar;
cb.Label.String = 'Manual Lap Time (s)';
xlabel(sprintf('PC1 (%.1f%%)', explained(1)));
ylabel(sprintf('PC2 (%.1f%%)', explained(2)));
title([batchLabel ' Setup PCA - Manual Lap Time Scores']);
grid on; hold on;
for i = 1:height(TMAN)
    text(TMAN.PC1(i)+0.03, TMAN.PC2(i), TMAN.config_id{i}, 'FontSize', 9, 'Interpreter', 'none');
end
saveFigure(f4, outFolder, '04_manual_lap_time_scores');

%% -----------------------------
%% Figure 5: AI vs manual lap-time PCA overlay
f5 = figure('Color','w');
scatter(TAI.PC1, TAI.PC2, 130, TAI.Lap_Time_s, 'o', 'filled'); hold on;
scatter(TMAN.PC1, TMAN.PC2, 130, TMAN.Lap_Time_s, 's', 'filled');
colormap(whitejet(256));
cb = colorbar;
cb.Label.String = 'Lap Time (s)';
xlabel(sprintf('PC1 (%.1f%%)', explained(1)));
ylabel(sprintf('PC2 (%.1f%%)', explained(2)));
title([batchLabel ' Setup PCA - AI vs Manual Lap Time Scores']);
grid on;
for i = 1:height(TAI)
    text(TAI.PC1(i)+0.03, TAI.PC2(i), ['AI ' TAI.config_id{i}], 'FontSize', 8, 'Interpreter', 'none');
end
for i = 1:height(TMAN)
    text(TMAN.PC1(i)+0.03, TMAN.PC2(i)-0.04, ['MAN ' TMAN.config_id{i}], 'FontSize', 8, 'Interpreter', 'none');
end
legend('AI','Manual','Location','best');
saveFigure(f5, outFolder, '05_ai_manual_lap_time_overlay');

%% -----------------------------
%% Sector-time correlation heatmaps
sectorVars = {'0-100m_s','100-200m_s','200-300m_s','300-400m_s','400-470m_s'};

corrAI_Sectors  = sectorCorrelationMatrix(TAI,  setupVars, sectorVars);
corrMAN_Sectors = sectorCorrelationMatrix(TMAN, setupVars, sectorVars);

%% Figure 6: AI sector-time heatmap
f6 = figure('Color','w', 'Position', [100 100 900 550]);
plotCorrelationHeatmap(corrAI_Sectors, setupVars, sectorVars, ...
    [batchLabel ' - Correlation of Setup Variables with AI Sector Times']);
saveFigure(f6, outFolder, '06_ai_sector_heatmap_whitejet');

%% Figure 7: Manual sector-time heatmap
f7 = figure('Color','w', 'Position', [100 100 900 550]);
plotCorrelationHeatmap(corrMAN_Sectors, setupVars, sectorVars, ...
    [batchLabel ' - Correlation of Setup Variables with Manual Sector Times']);
saveFigure(f7, outFolder, '07_manual_sector_heatmap_whitejet');

%% -----------------------------
%% Save numerical outputs
writetable(explainedTable, fullfile(outFolder, 'explained_variance.csv'));

loadingsTable = array2table(coeff(:,1:3), 'VariableNames', {'PC1','PC2','PC3'});
loadingsTable.Variable = setupVars';
loadingsTable = movevars(loadingsTable, 'Variable', 'Before', 1);
writetable(loadingsTable, fullfile(outFolder, 'setup_loadings.csv'));

writetable(scoreTable, fullfile(outFolder, 'config_scores.csv'));

AIsectorCorrTable = array2table(corrAI_Sectors, 'VariableNames', matlab.lang.makeValidName(sectorVars));
AIsectorCorrTable.Variable = setupVars';
AIsectorCorrTable = movevars(AIsectorCorrTable, 'Variable', 'Before', 1);
writetable(AIsectorCorrTable, fullfile(outFolder, 'AI_sector_correlations.csv'));

MANsectorCorrTable = array2table(corrMAN_Sectors, 'VariableNames', matlab.lang.makeValidName(sectorVars));
MANsectorCorrTable.Variable = setupVars';
MANsectorCorrTable = movevars(MANsectorCorrTable, 'Variable', 'Before', 1);
writetable(MANsectorCorrTable, fullfile(outFolder, 'MAN_sector_correlations.csv'));

disp(['All plots and tables saved to: ' outFolder]);

%% =============================
%% Local helper functions
function T = standardiseConfigColumn(T)
    names = T.Properties.VariableNames;

    if any(strcmp(names, 'Config')) && ~any(strcmp(names, 'config_id'))
        T.Properties.VariableNames{strcmp(names, 'Config')} = 'config_id';
    end

    if ~any(strcmp(T.Properties.VariableNames, 'config_id'))
        error('Could not find a Config or config_id column in the results table.');
    end

    T.config_id = cellstr(string(T.config_id));
end

function C = sectorCorrelationMatrix(T, setupVars, sectorVars)
    C = zeros(numel(setupVars), numel(sectorVars));

    for j = 1:numel(setupVars)
        for s = 1:numel(sectorVars)
            C(j,s) = corr(T{:, setupVars{j}}, T.(sectorVars{s}), ...
                'Type', 'Pearson', 'Rows', 'complete');
        end
    end
end

function plotCorrelationHeatmap(C, setupVars, sectorVars, chartTitle)
    imagesc(C);
    colormap(whitejet(256));
    caxis([-1 1]);
    cb = colorbar;
    cb.Label.String = 'Pearson correlation coefficient';

    set(gca, 'XTick', 1:numel(sectorVars), ...
             'XTickLabel', sectorVars, ...
             'YTick', 1:numel(setupVars), ...
             'YTickLabel', setupVars, ...
             'TickLabelInterpreter', 'none');

    xlabel('Sector');
    ylabel('Setup Variable');
    title(chartTitle);

    % Add correlation values inside each heatmap cell for thesis readability.
    for r = 1:size(C,1)
        for c = 1:size(C,2)
            val = C(r,c);
            if abs(val) > 0.55
                txtColour = 'w';
            else
                txtColour = 'k';
            end
            text(c, r, sprintf('%.2f', val), ...
                'HorizontalAlignment', 'center', ...
                'Color', txtColour, ...
                'FontSize', 8);
        end
    end
end

function saveFigure(figHandle, outFolder, fileBase)
    pngPath = fullfile(outFolder, [fileBase '.png']);
    figPath = fullfile(outFolder, [fileBase '.fig']);

    try
        exportgraphics(figHandle, pngPath, 'Resolution', 300);
    catch
        saveas(figHandle, pngPath);
    end

    savefig(figHandle, figPath);
end

function cmap = whitejet(m)
    % WHITEJET  Jet-style diverging colormap with white at the centre.
    % Useful for correlation heatmaps where zero should appear neutral.
    if nargin < 1
        m = 256;
    end

    lowerN = floor(m/2);
    upperN = m - lowerN;

    blueSide = [linspace(0,1,lowerN)', linspace(0,1,lowerN)', ones(lowerN,1)];
    redSide  = [ones(upperN,1), linspace(1,0,upperN)', linspace(1,0,upperN)'];

    cmap = [blueSide; redSide];

    % Widen the white band slightly around the centre so near-zero
    % correlations stand out clearly.
    centre = round(m/2);
    whiteWidth = max(2, round(0.025*m));
    idx = max(1, centre-whiteWidth):min(m, centre+whiteWidth);
    cmap(idx,:) = 1;
end
