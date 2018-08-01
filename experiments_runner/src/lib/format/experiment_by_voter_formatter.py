from lib.packages import *

class ExperimentByVoterFormatter():

    def __init__(self, election_dates, contact_types, table_puller_obj):
        self.election_dates = {(pd.to_datetime(row['start']), pd.to_datetime(row['end'])): (row['year'],row['election']) \
                                for idx,row in election_dates.iterrows()}
        self.c_types = contact_types.method
        self.exp_results_df = table_puller_obj.experiments#[table_puller_obj.experiments >= 2016]
        self.contacts_df = table_puller_obj.contact_history
        self.persons = table_puller_obj.persons
        self.elections = self.exp_results_df.election_w_year.unique()

        self.experiment_dfs = []

    def set_election(self):

        self.contacts_df['datecanvassed'] = pd.to_datetime(self.contacts_df['datecanvassed'])

        def election(x):
            for dates, election in self.election_dates.items():
                if x.datecanvassed >= dates[0] and x.datecanvassed <= dates[1]:
                    return election[1] + ' - ' + str(election[0])

        self.contacts_df['election_w_year'] = self.contacts_df.apply(election,axis=1)

    def experiment_results_by_election(self):

        for election in self.elections:
            election_subset = self.contacts_df[(self.contacts_df.election_w_year == election) \
                                            & (self.contacts_df.contacttype.isin(self.c_types)) \
                                            & (self.contacts_df.result.isin(['CANVASSED', 'LEFT MESSAGE']))]

            for org in election_subset.org.unique():

                org_subset, non_org_subset = self.subset_org_and_non_org(election_subset, org)

                exp_info = self.exp_results_df[(self.exp_results_df.election_w_year == election) \
                                               & (self.exp_results_df.org == org)]

                combined = self.merge_org_w_non_org(org_subset, non_org_subset, exp_info)

                if not combined.empty:
                    self.experiment_dfs.append(combined)

    def subset_org_and_non_org(self, election_subset, org):

        org_subset = election_subset[(election_subset.org == org)] \
                .groupby(['vanid','org','contacttype'])[['dwid']].count().unstack().fillna(0)
        non_org_subset = election_subset[(election_subset.org != org)] \
                .groupby(['vanid','org','contacttype'])[['dwid']].count().unstack().fillna(0)

        return org_subset, non_org_subset

    def merge_org_w_non_org(self, org, non_org, exp_info):

        org = org.set_index(org.index.droplevel(1))
        org.columns = [ct + '_org' for ct in org.columns.levels[1].tolist()]
        non_org = non_org.set_index(non_org.index.droplevel(1))
        non_org.columns = [ct + '_non_org' for ct in non_org.columns.levels[1].tolist()]
        combined = org.join(non_org,how='left').reset_index()

        combined_w_info = exp_info.merge(combined,on='vanid',how='left')

        return combined_w_info

    def combine_all_experiment_results(self):
        self.all_experiments = pd.concat(self.experiment_dfs).fillna(0)

    def merge_all_exps_w_persons(self):
        self.persons['vanid'] = self.persons.vanid.astype(float).astype('int64')
        self.voter_df = self.all_experiments.merge(self.persons,on='vanid',how='left')
        self.voter_df.to_csv('voter_df.csv')


    def run(self):
        self.set_election()
        self.experiment_results_by_election()
        self.combine_all_experiment_results()
        self.merge_all_exps_w_persons()
